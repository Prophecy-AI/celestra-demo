"""
Web search tool using Tavily API for agent_v3
"""
import os
from typing import Dict, Any, List
from tavily import TavilyClient
from .base import Tool, ToolResult


class WebSearchTool(Tool):
    """Tool for web searching using Tavily API with pharmaceutical context enhancement"""

    def __init__(self):
        super().__init__(
            name="web_search",
            description="Search the web for information using Tavily API with pharmaceutical domain optimization"
        )
        self.tavily_client = None
        self._initialize_client()
        self._pharmaceutical_domains = [
            "fda.gov",
            "clinicaltrials.gov",
            "pubmed.ncbi.nlm.nih.gov",
            "nejm.org",
            "jamanetwork.com",
            "thelancet.com"
        ]

    def _initialize_client(self):
        """Initialize Tavily client with API key from environment"""
        api_key = os.getenv("TAVILY_API_KEY")
        if not api_key:
            raise ValueError("TAVILY_API_KEY not found in environment variables")

        try:
            self.tavily_client = TavilyClient(api_key=api_key)
        except Exception as e:
            raise ValueError(f"Failed to initialize Tavily client: {str(e)}")

    def execute(self, parameters: Dict[str, Any], context: Any) -> ToolResult:
        """
        Execute web search using Tavily API with pharmaceutical context enhancement

        Parameters:
        - query: The search query string
        - max_results: Maximum number of results to return (default: 5)
        - search_depth: Either 'basic' or 'advanced' (default: 'basic')
        - include_answer: Whether to include AI-generated answer (default: True)
        - include_raw_content: Whether to include raw content (default: False)
        - pharmaceutical_focused: Whether to prioritize pharmaceutical domains (default: auto-detect)
        """
        # Validate required parameters
        validation_error = self.validate_parameters(parameters, ["query"])
        if validation_error:
            return ToolResult(success=False, data={}, error=validation_error)

        query = parameters["query"]
        max_results = parameters.get("max_results", 5)
        search_depth = parameters.get("search_depth", "basic")
        include_answer = parameters.get("include_answer", True)
        include_raw_content = parameters.get("include_raw_content", False)

        # Auto-detect if query is pharmaceutical-related
        pharmaceutical_focused = parameters.get("pharmaceutical_focused", self._is_pharmaceutical_query(query))

        # Enhance query for pharmaceutical context if needed
        enhanced_query = self._enhance_pharmaceutical_query(query) if pharmaceutical_focused else query

        try:
            # Perform the search with pharmaceutical domain preference if applicable
            search_params = {
                "query": enhanced_query,
                "max_results": max_results,
                "search_depth": search_depth,
                "include_answer": include_answer,
                "include_raw_content": include_raw_content
            }

            # NOTE: Domain filtering removed - it was too restrictive
            # Tavily was only returning FDA regulatory docs instead of marketing/industry content
            # Let Tavily's relevance ranking find the best sources naturally

            response = self.tavily_client.search(**search_params)

            # Format the results for context
            formatted_results = {
                "query": query,
                "enhanced_query": enhanced_query if enhanced_query != query else None,
                "answer": response.get("answer", ""),
                "pharmaceutical_context": pharmaceutical_focused,
                "results": []
            }

            # Process search results with pharmaceutical context extraction
            for result in response.get("results", []):
                formatted_result = {
                    "title": result.get("title", ""),
                    "url": result.get("url", ""),
                    "content": result.get("content", ""),
                    "score": result.get("score", 0)
                }

                # Extract pharmaceutical-specific insights if relevant
                if pharmaceutical_focused:
                    formatted_result["pharmaceutical_insights"] = self._extract_pharmaceutical_insights(
                        result.get("content", "")
                    )

                formatted_results["results"].append(formatted_result)

            # Generate consolidated pharmaceutical facts if applicable
            if pharmaceutical_focused:
                formatted_results["consolidated_facts"] = self._consolidate_pharmaceutical_facts(
                    formatted_results["results"]
                )

            return ToolResult(
                success=True,
                data={
                    "search_results": formatted_results,
                    "total_results": len(formatted_results["results"]),
                    "message": f"Found {len(formatted_results['results'])} results for query: '{query}'" +
                              (f" (pharmaceutical-focused)" if pharmaceutical_focused else "")
                }
            )

        except Exception as e:
            return ToolResult(
                success=False,
                data={},
                error=f"Web search failed: {str(e)}"
            )

    def _is_pharmaceutical_query(self, query: str) -> bool:
        """Detect if query is pharmaceutical/clinical related"""
        pharma_keywords = [
            "prescriber", "prescription", "drug", "medication", "pharmaceutical",
            "clinical", "nbrx", "trx", "persistence", "refill", "adherence",
            "fda", "indication", "treatment", "therapy", "patient", "physician",
            "hcp", "provider", "launch", "adoption", "formulary"
        ]
        query_lower = query.lower()
        return any(keyword in query_lower for keyword in pharma_keywords)

    def _enhance_pharmaceutical_query(self, query: str) -> str:
        """Enhance query with pharmaceutical context keywords"""
        # Add context terms to improve search quality
        if "prescriber" in query.lower() or "prediction" in query.lower():
            if "behavior" not in query.lower():
                query = f"{query} prescriber behavior patterns"
        if "early" in query.lower() and "indicator" in query.lower():
            if "launch" not in query.lower():
                query = f"{query} pharmaceutical launch adoption"
        return query

    def _extract_pharmaceutical_insights(self, content: str) -> Dict[str, Any]:
        """Extract structured pharmaceutical insights from content"""
        insights = {
            "mentions_metrics": False,
            "mentions_thresholds": False,
            "mentions_patterns": False
        }

        content_lower = content.lower()

        # Check for key pharmaceutical concepts
        if any(term in content_lower for term in ["nbrx", "trx", "prescription volume", "rx count"]):
            insights["mentions_metrics"] = True

        if any(term in content_lower for term in ["threshold", "benchmark", "top prescriber", "high prescriber"]):
            insights["mentions_thresholds"] = True

        if any(term in content_lower for term in ["pattern", "behavior", "adoption", "trajectory", "trend"]):
            insights["mentions_patterns"] = True

        return insights

    def _consolidate_pharmaceutical_facts(self, results: List[Dict[str, Any]]) -> List[str]:
        """Consolidate pharmaceutical facts from multiple search results"""
        facts = []

        # Extract key facts from high-scoring results
        for result in results[:3]:  # Top 3 results
            content = result.get("content", "")
            if not content:
                continue

            # Extract sentences mentioning key concepts
            sentences = content.split(". ")
            for sentence in sentences:
                sentence_lower = sentence.lower()
                # Look for actionable facts
                if any(keyword in sentence_lower for keyword in [
                    "prescriber", "prediction", "early", "indicator", "pattern",
                    "nbrx", "volume", "growth", "adoption", "high prescriber"
                ]) and len(sentence) > 30:
                    facts.append(sentence.strip())
                    if len(facts) >= 5:  # Limit to 5 key facts
                        break
            if len(facts) >= 5:
                break

        return facts


class ClinicalContextSearchTool(Tool):
    """Specialized tool for searching clinical/medical context"""

    def __init__(self):
        super().__init__(
            name="clinical_context_search",
            description="Search for clinical and medical context using Tavily API"
        )
        self.tavily_client = None
        self._initialize_client()

    def _initialize_client(self):
        """Initialize Tavily client with API key from environment"""
        api_key = os.getenv("TAVILY_API_KEY")
        if not api_key:
            raise ValueError("TAVILY_API_KEY not found in environment variables")

        try:
            self.tavily_client = TavilyClient(api_key=api_key)
        except Exception as e:
            raise ValueError(f"Failed to initialize Tavily client: {str(e)}")

    def execute(self, parameters: Dict[str, Any], context: Any) -> ToolResult:
        """
        Execute clinical context search

        Parameters:
        - drug_name: Name of the drug/medication
        - condition: Medical condition (optional)
        - search_type: Type of search ('indication', 'prescribing_pattern', 'clinical_trial', 'general')
        """
        # Validate required parameters
        validation_error = self.validate_parameters(parameters, ["drug_name"])
        if validation_error:
            return ToolResult(success=False, data={}, error=validation_error)

        drug_name = parameters["drug_name"]
        condition = parameters.get("condition", "")
        search_type = parameters.get("search_type", "general")

        # Build context-specific query
        query_templates = {
            "indication": f"{drug_name} FDA approved indications clinical use",
            "prescribing_pattern": f"{drug_name} prescribing patterns physician behavior",
            "clinical_trial": f"{drug_name} clinical trials efficacy results",
            "general": f"{drug_name} clinical information prescribing guidelines"
        }

        if condition:
            query_templates[search_type] = f"{drug_name} {condition} {query_templates[search_type]}"

        query = query_templates.get(search_type, query_templates["general"])

        try:
            # Perform the search with medical context focus
            response = self.tavily_client.search(
                query=query,
                max_results=3,
                search_depth="advanced",
                include_answer=True,
                include_domains=["fda.gov", "clinicaltrials.gov", "pubmed.ncbi.nlm.nih.gov", "uptodate.com"]
            )

            # Format clinical context
            clinical_context = {
                "drug": drug_name,
                "condition": condition,
                "search_type": search_type,
                "clinical_summary": response.get("answer", ""),
                "sources": []
            }

            # Process clinical sources
            for result in response.get("results", []):
                source = {
                    "title": result.get("title", ""),
                    "url": result.get("url", ""),
                    "content": result.get("content", "")[:500] + "..." if len(result.get("content", "")) > 500 else result.get("content", ""),
                    "relevance_score": result.get("score", 0)
                }
                clinical_context["sources"].append(source)

            return ToolResult(
                success=True,
                data={
                    "clinical_context": clinical_context,
                    "message": f"Retrieved clinical context for {drug_name}"
                }
            )

        except Exception as e:
            return ToolResult(
                success=False,
                data={},
                error=f"Clinical context search failed: {str(e)}"
            )