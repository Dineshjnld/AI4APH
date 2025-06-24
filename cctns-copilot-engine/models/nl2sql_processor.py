"""
Natural Language to SQL Processor for CCTNS
"""
import re
import sqlparse
from typing import Dict, Optional, List
import logging

class NL2SQLProcessor:
    def __init__(self, schema_config: dict):
        self.logger = logging.getLogger(__name__)
        self.schema = schema_config
        self.tables = {table["name"]: table for table in schema_config["tables"]}
    
    async def generate_sql(self, query: str) -> Dict:
        """Generate SQL from natural language"""
        try:
            # Rule-based approach for CCTNS queries
            sql = self._rule_based_generation(query)
            if sql:
                return {
                    "sql": sql,
                    "confidence": 0.9,
                    "method": "rule_based",
                    "valid": self._validate_sql(sql)
                }
            
            return {"sql": "", "confidence": 0.0, "error": "No matching pattern"}
            
        except Exception as e:
            return {"sql": "", "confidence": 0.0, "error": str(e)}
    
    def _rule_based_generation(self, query: str) -> Optional[str]:
        """Rule-based SQL generation for common patterns"""
        query_lower = query.lower()
        
        # Pattern 1: District crime summary
        if "crimes" in query_lower and "district" in query_lower:
            district = self._extract_district(query_lower)
            if district:
                return f"""
                SELECT ct.description as crime_type, COUNT(*) as count
                FROM FIR f
                JOIN DISTRICT_MASTER d ON f.district_id = d.district_id
                JOIN CRIME_TYPE_MASTER ct ON f.crime_type_id = ct.crime_type_id
                WHERE d.district_name = '{district}'
                GROUP BY ct.description
                ORDER BY count DESC
                """
        
        # Pattern 2: Officer performance
        if "officer" in query_lower and ("arrest" in query_lower or "performance" in query_lower):
            return """
            SELECT o.officer_name, o.rank, COUNT(a.arrest_id) as arrests
            FROM OFFICER_MASTER o
            LEFT JOIN ARREST a ON o.officer_id = a.officer_id
            WHERE a.arrest_date >= TRUNC(SYSDATE, 'MM')
            GROUP BY o.officer_name, o.rank
            ORDER BY arrests DESC
            """
        
        # Pattern 3: FIR counts
        if "fir" in query_lower and "count" in query_lower:
            if "today" in query_lower:
                return "SELECT COUNT(*) as fir_count FROM FIR WHERE DATE(incident_date) = DATE(SYSDATE)"
            elif "month" in query_lower:
                return "SELECT COUNT(*) as fir_count FROM FIR WHERE incident_date >= TRUNC(SYSDATE, 'MM')"
        
        return None
    
    def _extract_district(self, query: str) -> Optional[str]:
        """Extract district name from query"""
        districts = ["guntur", "vijayawada", "visakhapatnam", "tirupati", "kurnool"]
        for district in districts:
            if district in query:
                return district.title()
        return None
    
    def _validate_sql(self, sql: str) -> bool:
        """Validate SQL syntax"""
        try:
            parsed = sqlparse.parse(sql)
            return len(parsed) > 0
        except:
            return False