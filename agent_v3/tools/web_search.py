"""
Web search tool using Tavily API for agent_v3
"""
import os
from typing import Dict, Any
from tavily import TavilyClient
from .base import Tool, ToolResult


class WebSearchTool(Tool):
    """Tool for web searching using Tavily API"""

    def __init__(self):
        super().__init__(
            name="web_search",
            description="Search the web for information using Tavily API"
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
        Execute web search using Tavily API

        Parameters:
        - query: The search query string
        - max_results: Maximum number of results to return (default: 5)
        - search_depth: Either 'basic' or 'advanced' (default: 'basic')
        - include_answer: Whether to include AI-generated answer (default: True)
        - include_raw_content: Whether to include raw content (default: False)
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

        try:
            # Perform the search
            search_params = {
                "query": query,
                "max_results": max_results,
                "search_depth": search_depth,
                "include_answer": include_answer,
                "include_raw_content": include_raw_content
            }

            response = self.tavily_client.search(**search_params)

            # Format the results for context
            formatted_results = {
                "query": query,
                "answer": response.get("answer", ""),
                "results": []
            }

            # Process search results
            for result in response.get("results", []):
                formatted_result = {
                    "title": result.get("title", ""),
                    "url": result.get("url", ""),
                    "content": result.get("content", ""),
                    "score": result.get("score", 0)
                }
                formatted_results["results"].append(formatted_result)

            return ToolResult(
                success=True,
                data={
                    "search_results": formatted_results,
                    "total_results": len(formatted_results["results"]),
                    "message": f"Found {len(formatted_results['results'])} results for query: '{query}'"
                }
            )

        except Exception as e:
            return ToolResult(
                success=False,
                data={},
                error=f"Web search failed: {str(e)}"
            )


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