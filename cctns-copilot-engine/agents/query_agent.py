"""
Query Agent for natural language to SQL conversion
"""
from typing import Dict, Any, List
from .base_agent import BaseAgent
from models.nl2sql_processor import NL2SQLProcessor
from models.schema_manager import SchemaManager

class QueryAgent(BaseAgent):
    """Agent specialized in NL to SQL query generation"""
    
    def __init__(self, config: Dict[str, Any], schema_manager: SchemaManager):
        super().__init__("QueryAgent", config)
        
        self.nl2sql_processor = NL2SQLProcessor(config.get("cctns_schema", {}))
        self.schema_manager = schema_manager
        
        # Query generation settings
        self.max_query_complexity = config.get("max_complexity", 10)
        self.allowed_operations = config.get("allowed_operations", ["SELECT"])
    
    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process natural language query and generate SQL"""
        
        query_text = input_data.get("text", "")
        context = input_data.get("context", {})
        query_type = input_data.get("query_type", "standard")
        
        if query_type == "standard":
            return await self._generate_standard_query(query_text, context)
        elif query_type == "complex":
            return await self._generate_complex_query(query_text, context)
        elif query_type == "analytical":
            return await self._generate_analytical_query(query_text, context)
        else:
            raise ValueError(f"Unsupported query type: {query_type}")
    
    async def _generate_standard_query(self, query_text: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate standard SQL query"""
        
        # Step 1: Generate SQL using NL2SQL processor
        sql_result = await self.nl2sql_processor.generate_sql(query_text)
        
        if not sql_result.get("valid"):
            return {
                "sql": "",
                "confidence": 0.0,
                "error": sql_result.get("error", "SQL generation failed"),
                "suggestions": await self._get_query_suggestions(query_text)
            }
        
        # Step 2: Enhance with schema information
        enhanced_sql = await self._enhance_with_schema(sql_result["sql"], context)
        
        # Step 3: Validate and optimize
        validation_result = await self._validate_query(enhanced_sql)
        
        return {
            "sql": enhanced_sql,
            "original_sql": sql_result["sql"],
            "confidence": sql_result["confidence"],
            "method": sql_result["method"],
            "validation": validation_result,
            "estimated_rows": await self._estimate_result_size(enhanced_sql),
            "execution_plan": await self._get_execution_plan(enhanced_sql),
            "suggested_optimizations": await self._get_optimization_suggestions(enhanced_sql)
        }
    
    async def _generate_complex_query(self, query_text: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate complex analytical SQL query"""
        
        # Parse complex requirements
        query_components = await self._parse_complex_query(query_text)
        
        # Generate base query
        base_result = await self._generate_standard_query(query_text, context)
        
        if not base_result.get("sql"):
            return base_result
        
        # Enhance with complex features
        enhanced_sql = await self._add_complex_features(
            base_result["sql"], 
            query_components
        )
        
        return {
            **base_result,
            "sql": enhanced_sql,
            "complexity_level": "high",
            "query_components": query_components
        }
    
    async def _generate_analytical_query(self, query_text: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate analytical/reporting SQL query"""
        
        # Identify analytical patterns
        analytical_patterns = await self._identify_analytical_patterns(query_text)
        
        # Generate base query
        base_result = await self._generate_standard_query(query_text, context)
        
        if not base_result.get("sql"):
            return base_result
        
        # Add analytical features
        analytical_sql = await self._add_analytical_features(
            base_result["sql"],
            analytical_patterns
        )
        
        return {
            **base_result,
            "sql": analytical_sql,
            "analytical_patterns": analytical_patterns,
            "visualization_suggestions": await self._suggest_visualizations(analytical_patterns)
        }
    
    async def _enhance_with_schema(self, sql: str, context: Dict[str, Any]) -> str:
        """Enhance SQL with schema-aware improvements"""
        
        # Extract table names from SQL
        mentioned_tables = self._extract_table_names(sql)
        
        # Get schema information
        schema_info = {}
        for table in mentioned_tables:
            info = self.schema_manager.get_table_info(table)
            if info:
                schema_info[table] = info
        
        # Suggest proper JOINs
        if len(mentioned_tables) > 1:
            join_suggestions = self.schema_manager.suggest_joins_for_query(mentioned_tables)
            # Apply suggested JOINs if not already present
            for join in join_suggestions:
                if join["condition"] not in sql:
                    sql = self._add_join_to_sql(sql, join)
        
        # Add proper aliases and qualifications
        sql = self._add_table_aliases(sql, mentioned_tables)
        
        return sql
    
    async def _validate_query(self, sql: str) -> Dict[str, Any]:
        """Validate generated SQL query"""
        validation_result = {
            "syntax_valid": True,
            "security_valid": True,
            "performance_warnings": [],
            "semantic_warnings": []
        }
        
        # Syntax validation
        try:
            import sqlparse
            parsed = sqlparse.parse(sql)
            if not parsed:
                validation_result["syntax_valid"] = False
        except:
            validation_result["syntax_valid"] = False
        
        # Security validation
        security_check = self._check_query_security(sql)
        validation_result["security_valid"] = security_check["safe"]
        if not security_check["safe"]:
            validation_result["security_warnings"] = security_check["warnings"]
        
        # Performance validation
        perf_warnings = self._check_query_performance(sql)
        validation_result["performance_warnings"] = perf_warnings
        
        return validation_result
    
    async def _estimate_result_size(self, sql: str) -> Dict[str, Any]:
        """Estimate query result size"""
        # Simple estimation based on table sizes and filters
        return {
            "estimated_rows": "unknown",
            "confidence": "low",
            "method": "heuristic"
        }
    
    async def _get_execution_plan(self, sql: str) -> Dict[str, Any]:
        """Get query execution plan"""
        # Would integrate with Oracle EXPLAIN PLAN
        return {
            "plan_available": False,
            "reason": "Execution plan analysis not implemented"
        }
    
    async def _get_optimization_suggestions(self, sql: str) -> List[str]:
        """Get query optimization suggestions"""
        suggestions = []
        
        # Check for missing indexes
        if "WHERE" in sql.upper() and "INDEX" not in sql.upper():
            suggestions.append("Consider adding indexes on WHERE clause columns")
        
        # Check for SELECT *
        if "SELECT *" in sql.upper():
            suggestions.append("Consider selecting specific columns instead of *")
        
        # Check for unnecessary ORDER BY
        if "ORDER BY" in sql.upper() and "LIMIT" not in sql.upper():
            suggestions.append("ORDER BY without LIMIT may impact performance")
        
        return suggestions
    
    def _extract_table_names(self, sql: str) -> List[str]:
        """Extract table names from SQL query"""
        import re
        # Simple regex to find table names after FROM and JOIN
        pattern = r'(?:FROM|JOIN)\s+([A-Za-z_][A-Za-z0-9_]*)'
        matches = re.findall(pattern, sql, re.IGNORECASE)
        return list(set(matches))
    
    def _check_query_security(self, sql: str) -> Dict[str, Any]:
        """Check query for security issues"""
        sql_upper = sql.upper()
        
        warnings = []
        
        # Check for dangerous operations
        dangerous_ops = ["DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "CREATE"]
        for op in dangerous_ops:
            if op in sql_upper:
                warnings.append(f"Dangerous operation detected: {op}")
        
        # Check for potential injection
        if "--" in sql or "/*" in sql:
            warnings.append("Potential SQL injection: comments detected")
        
        return {
            "safe": len(warnings) == 0,
            "warnings": warnings
        }
    
    def _check_query_performance(self, sql: str) -> List[str]:
        """Check query for performance issues"""
        warnings = []
        
        # Check for Cartesian products
        if sql.upper().count("FROM") > 1 and "WHERE" not in sql.upper():
            warnings.append("Potential Cartesian product: multiple tables without WHERE clause")
        
        # Check for functions in WHERE clause
        if any(func in sql.upper() for func in ["UPPER(", "LOWER(", "SUBSTR("]):
            warnings.append("Functions in WHERE clause may prevent index usage")
        
        return warnings
    
    async def _get_query_suggestions(self, failed_query: str) -> List[str]:
        """Get suggestions for failed queries"""
        suggestions = [
            "Try using simpler language",
            "Specify the exact table or data you're looking for",
            "Include specific date ranges or filters",
            "Use police-specific terms (FIR, SHO, district, etc.)"
        ]
        
        # Add context-specific suggestions based on query content
        query_lower = failed_query.lower()
        
        if "show" in query_lower or "display" in query_lower:
            suggestions.append("Try: 'List all crimes in [district name]'")
        
        if "count" in query_lower or "how many" in query_lower:
            suggestions.append("Try: 'Count FIRs registered this month'")
        
        if "officer" in query_lower:
            suggestions.append("Try: 'Show arrests made by officer [name]'")
        
        return suggestions
    
    def get_query_stats(self) -> Dict[str, Any]:
        """Get query generation statistics"""
        base_stats = self.get_status()
        
        query_stats = {
            "max_query_complexity": self.max_query_complexity,
            "allowed_operations": self.allowed_operations,
            "schema_manager_available": self.schema_manager is not None,
            "nl2sql_processor_available": self.nl2sql_processor is not None
        }
        
        return {**base_stats, "query_specific": query_stats}