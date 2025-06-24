"""
SQL Executor with Oracle Database connectivity and security
"""
import cx_Oracle
import sqlparse
import logging
import asyncio
from typing import Dict, List, Optional, Any, Union
from sqlalchemy import create_engine, text, MetaData
from sqlalchemy.exc import SQLAlchemyError
from contextlib import asynccontextmanager
import time
from config.settings import settings

class SQLExecutor:
    """Secure SQL execution against Oracle CCTNS database"""
    
    def __init__(self, connection_string: Optional[str] = None):
        self.logger = logging.getLogger(__name__)
        self.connection_string = connection_string or settings.ORACLE_CONNECTION_STRING
        self.engine = None
        self.metadata = None
        
        # Security settings
        self.max_results = settings.SQL_MAX_RESULTS
        self.timeout = settings.SQL_TIMEOUT
        
        # Query execution stats
        self.execution_stats = {
            "total_queries": 0,
            "successful_queries": 0,
            "failed_queries": 0,
            "avg_execution_time": 0.0
        }
        
        if self.connection_string:
            self._initialize_connection()
    
    def _initialize_connection(self):
        """Initialize database connection"""
        try:
            self.engine = create_engine(
                self.connection_string,
                pool_size=settings.DATABASE_POOL_SIZE,
                pool_pre_ping=True,
                pool_recycle=3600,
                echo=settings.DEBUG
            )
            
            # Test connection
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1 FROM DUAL"))
            
            # Load metadata
            self.metadata = MetaData()
            self.metadata.reflect(bind=self.engine)
            
            self.logger.info("✅ Oracle database connection established")
            
        except Exception as e:
            self.logger.error(f"❌ Database connection failed: {e}")
            self.engine = None
    
    async def execute_sql(self, sql: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Execute SQL query with security checks and error handling
        
        Args:
            sql: SQL query string
            params: Optional parameters for query
            
        Returns:
            Dict with results, metadata, and execution info
        """
        if not self.engine:
            return self._error_response("No database connection available")
        
        start_time = time.time()
        self.execution_stats["total_queries"] += 1
        
        try:
            # Security validation
            security_check = self._validate_sql_security(sql)
            if not security_check["valid"]:
                return self._error_response(f"Security validation failed: {security_check['reason']}")
            
            # SQL parsing and validation
            parsing_result = self._parse_and_validate_sql(sql)
            if not parsing_result["valid"]:
                return self._error_response(f"SQL validation failed: {parsing_result['reason']}")
            
            # Execute query with timeout
            result = await self._execute_with_timeout(sql, params)
            
            # Calculate execution time
            execution_time = time.time() - start_time
            self._update_execution_stats(execution_time, True)
            
            return {
                "success": True,
                "results": result["data"],
                "columns": result["columns"],
                "row_count": len(result["data"]),
                "execution_time": execution_time,
                "sql_executed": sql,
                "metadata": {
                    "query_type": parsing_result["query_type"],
                    "tables_accessed": parsing_result["tables"],
                    "timestamp": time.time()
                }
            }
            
        except Exception as e:
            execution_time = time.time() - start_time
            self._update_execution_stats(execution_time, False)
            self.logger.error(f"SQL execution error: {e}")
            return self._error_response(str(e))
    
    def _validate_sql_security(self, sql: str) -> Dict[str, Union[bool, str]]:
        """Validate SQL for security threats"""
        sql_upper = sql.upper().strip()
        
        # Check for dangerous operations
        dangerous_keywords = [
            'DROP', 'DELETE', 'UPDATE', 'INSERT', 'ALTER', 'CREATE', 
            'TRUNCATE', 'REPLACE', 'MERGE', 'GRANT', 'REVOKE',
            'EXECUTE', 'EXEC', 'CALL', 'DECLARE', 'BEGIN', 'END'
        ]
        
        for keyword in dangerous_keywords:
            if f' {keyword} ' in f' {sql_upper} ' or sql_upper.startswith(keyword):
                return {
                    "valid": False,
                    "reason": f"Dangerous keyword '{keyword}' not allowed"
                }
        
        # Only allow SELECT statements
        if not sql_upper.startswith('SELECT'):
            return {
                "valid": False,
                "reason": "Only SELECT statements are allowed"
            }
        
        # Check for SQL injection patterns
        injection_patterns = [
            r"'.*OR.*'.*='.*'",
            r"'.*UNION.*SELECT",
            r"--",
            r"/\*.*\*/",
            r"xp_cmdshell",
            r"sp_.*"
        ]
        
        import re
        for pattern in injection_patterns:
            if re.search(pattern, sql, re.IGNORECASE):
                return {
                    "valid": False,
                    "reason": f"Potential SQL injection detected: {pattern}"
                }
        
        # Check query complexity (prevent DoS)
        if sql.count('JOIN') > 10:
            return {
                "valid": False,
                "reason": "Too many JOINs (max 10 allowed)"
            }
        
        if sql.count('SELECT') > 5:
            return {
                "valid": False,
                "reason": "Too many subqueries (max 5 allowed)"
            }
        
        return {"valid": True, "reason": "Security validation passed"}
    
    def _parse_and_validate_sql(self, sql: str) -> Dict[str, Any]:
        """Parse and validate SQL syntax"""
        try:
            parsed = sqlparse.parse(sql)
            if not parsed:
                return {"valid": False, "reason": "Failed to parse SQL"}
            
            statement = parsed[0]
            
            # Extract query information
            query_info = {
                "valid": True,
                "query_type": self._get_query_type(statement),
                "tables": self._extract_tables(statement),
                "columns": self._extract_columns(statement)
            }
            
            # Validate table access
            allowed_tables = [
                'DISTRICT_MASTER', 'STATION_MASTER', 'OFFICER_MASTER',
                'CRIME_TYPE_MASTER', 'FIR', 'ARREST'
            ]
            
            for table in query_info["tables"]:
                if table.upper() not in allowed_tables:
                    return {
                        "valid": False,
                        "reason": f"Access to table '{table}' not allowed"
                    }
            
            return query_info
            
        except Exception as e:
            return {"valid": False, "reason": f"SQL parsing error: {str(e)}"}
    
    def _get_query_type(self, statement) -> str:
        """Extract query type from parsed statement"""
        for token in statement.flatten():
            if token.ttype in sqlparse.tokens.Keyword:
                return token.value.upper()
        return "UNKNOWN"
    
    def _extract_tables(self, statement) -> List[str]:
        """Extract table names from SQL statement"""
        tables = []
        from_seen = False
        
        for token in statement.flatten():
            if token.ttype is sqlparse.tokens.Keyword and token.value.upper() == 'FROM':
                from_seen = True
            elif from_seen and token.ttype is None and token.value.strip():
                table_name = token.value.strip().split()[0]
                if table_name.upper() not in ['WHERE', 'JOIN', 'LEFT', 'RIGHT', 'INNER', 'OUTER']:
                    tables.append(table_name)
        
        return tables
    
    def _extract_columns(self, statement) -> List[str]:
        """Extract column names from SQL statement"""
        columns = []
        select_seen = False
        
        for token in statement.flatten():
            if token.ttype is sqlparse.tokens.Keyword and token.value.upper() == 'SELECT':
                select_seen = True
            elif select_seen and token.ttype is sqlparse.tokens.Keyword and token.value.upper() == 'FROM':
                break
            elif select_seen and token.ttype is None and token.value.strip():
                col_name = token.value.strip()
                if col_name != ',' and col_name != '*':
                    columns.append(col_name)
        
        return columns
    
    async def _execute_with_timeout(self, sql: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Execute SQL with timeout protection"""
        try:
            with self.engine.connect() as conn:
                # Set query timeout
                conn.execute(text(f"ALTER SESSION SET query_timeout = {self.timeout}"))
                
                # Execute main query
                result = conn.execute(text(sql), params or {})
                
                # Fetch results with limit
                rows = result.fetchmany(self.max_results)
                columns = list(result.keys())
                
                # Convert to list of dictionaries
                data = [dict(zip(columns, row)) for row in rows]
                
                return {
                    "data": data,
                    "columns": columns
                }
                
        except Exception as e:
            raise SQLAlchemyError(f"Query execution failed: {str(e)}")
    
    def _update_execution_stats(self, execution_time: float, success: bool):
        """Update execution statistics"""
        if success:
            self.execution_stats["successful_queries"] += 1
        else:
            self.execution_stats["failed_queries"] += 1
        
        # Update average execution time
        total_queries = self.execution_stats["total_queries"]
        current_avg = self.execution_stats["avg_execution_time"]
        self.execution_stats["avg_execution_time"] = (
            (current_avg * (total_queries - 1) + execution_time) / total_queries
        )
    
    def _error_response(self, error_message: str) -> Dict[str, Any]:
        """Generate standardized error response"""
        return {
            "success": False,
            "error": error_message,
            "results": [],
            "columns": [],
            "row_count": 0,
            "execution_time": 0.0,
            "metadata": {
                "timestamp": time.time()
            }
        }
    
    async def get_schema_info(self) -> Dict[str, Any]:
        """Get database schema information"""
        if not self.metadata:
            return {"error": "No metadata available"}
        
        schema_info = {}
        for table_name, table in self.metadata.tables.items():
            schema_info[table_name] = {
                "columns": [
                    {
                        "name": col.name,
                        "type": str(col.type),
                        "nullable": col.nullable,
                        "primary_key": col.primary_key
                    }
                    for col in table.columns
                ],
                "foreign_keys": [
                    {
                        "column": fk.parent.name,
                        "references": f"{fk.column.table.name}.{fk.column.name}"
                    }
                    for fk in table.foreign_keys
                ]
            }
        
        return schema_info
    
    def get_execution_stats(self) -> Dict[str, Any]:
        """Get execution statistics"""
        return self.execution_stats.copy()
    
    async def test_connection(self) -> Dict[str, Any]:
        """Test database connection"""
        try:
            result = await self.execute_sql("SELECT 'Connection OK' as status, SYSDATE as current_time FROM DUAL")
            return {
                "connected": result["success"],
                "details": result.get("results", [{}])[0] if result["success"] else None,
                "error": result.get("error") if not result["success"] else None
            }
        except Exception as e:
            return {
                "connected": False,
                "error": str(e)
            }