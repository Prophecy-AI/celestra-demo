"""
Test script for Tavily, Critic Agent, and Multi-Agent workflow integration
"""
import sys
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_tavily_configuration():
    """Test that Tavily API key is configured correctly"""
    print("Testing Tavily configuration...")

    try:
        tavily_key = os.getenv("TAVILY_API_KEY")
        if not tavily_key:
            print("✗ TAVILY_API_KEY not found in environment")
            return False

        if not tavily_key.startswith("tvly-"):
            print("✗ TAVILY_API_KEY format appears invalid")
            return False

        print(f"✓ TAVILY_API_KEY configured: {tavily_key[:10]}...")
        return True

    except Exception as e:
        print(f"✗ Tavily configuration test failed: {e}")
        return False

def test_tavily_tool_import():
    """Test that Tavily tools can be imported"""
    print("\nTesting Tavily tool imports...")

    try:
        from agent_v3.tools.web_search import WebSearchTool, ClinicalContextSearchTool
        print("✓ WebSearchTool imported successfully")
        print("✓ ClinicalContextSearchTool imported successfully")
        return True
    except Exception as e:
        print(f"✗ Tavily tool import failed: {e}")
        return False

def test_tavily_tool_initialization():
    """Test that Tavily tools can be initialized"""
    print("\nTesting Tavily tool initialization...")

    try:
        from agent_v3.tools.web_search import WebSearchTool, ClinicalContextSearchTool

        # Test WebSearchTool
        try:
            web_search = WebSearchTool()
            print("✓ WebSearchTool initialized successfully")
        except Exception as e:
            print(f"✗ WebSearchTool initialization failed: {e}")
            return False

        # Test ClinicalContextSearchTool
        try:
            clinical_search = ClinicalContextSearchTool()
            print("✓ ClinicalContextSearchTool initialized successfully")
        except Exception as e:
            print(f"✗ ClinicalContextSearchTool initialization failed: {e}")
            return False

        return True

    except Exception as e:
        print(f"✗ Tavily tool initialization test failed: {e}")
        return False

def test_critic_agent_import():
    """Test that Critic Agent can be imported"""
    print("\nTesting Critic Agent import...")

    try:
        from agent_v3.agents import CriticAgent
        print("✓ CriticAgent imported successfully")
        return True
    except Exception as e:
        print(f"✗ CriticAgent import failed: {e}")
        return False

def test_critic_agent_initialization():
    """Test that Critic Agent can be initialized"""
    print("\nTesting Critic Agent initialization...")

    try:
        from agent_v3.agents import CriticAgent

        critic = CriticAgent()
        print(f"✓ CriticAgent initialized: {critic.name}")
        print(f"✓ Allowed tools: {critic.allowed_tools}")
        return True

    except Exception as e:
        print(f"✗ CriticAgent initialization failed: {e}")
        return False

def test_multi_agent_workflow_components():
    """Test that all multi-agent workflow components are available"""
    print("\nTesting multi-agent workflow components...")

    try:
        from agent_v3.agents import PlannerAgent, RetrieverAgent, AnswererAgent, CriticAgent

        agents = {
            "planner": PlannerAgent(),
            "retriever": RetrieverAgent(),
            "answerer": AnswererAgent(),
            "critic": CriticAgent()
        }

        for agent_name, agent in agents.items():
            print(f"✓ {agent_name} agent ready: {agent.name}")

        return True

    except Exception as e:
        print(f"✗ Multi-agent workflow component test failed: {e}")
        return False

def test_pharmaceutical_features():
    """Test that pharmaceutical feature engineering is available"""
    print("\nTesting pharmaceutical feature engineering...")

    try:
        from agent_v3.tools.pharmaceutical_features import PharmaceuticalFeatureEngineeringTool

        pharma_tool = PharmaceuticalFeatureEngineeringTool()
        print(f"✓ Pharmaceutical feature engineering tool initialized: {pharma_tool.name}")
        return True

    except Exception as e:
        print(f"✗ Pharmaceutical feature engineering test failed: {e}")
        return False

def test_context_enhancements():
    """Test that Context enhancements are working"""
    print("\nTesting Context enhancements...")

    try:
        from agent_v3.context import Context

        # Create test context
        context = Context("test_session")

        # Test metadata functionality
        context.add_metadata("test_key", {"test": "value"})
        retrieved = context.get_metadata("test_key")
        assert retrieved == {"test": "value"}, "Metadata storage failed"
        print("✓ Context metadata functionality working")

        # Test conversation_history attribute
        assert hasattr(context, 'conversation_history'), "Missing conversation_history attribute"
        print("✓ Context has conversation_history attribute")

        return True

    except Exception as e:
        print(f"✗ Context enhancement test failed: {e}")
        return False

def test_predictive_analysis_tool():
    """Test that PredictiveAnalysisTool is properly configured"""
    print("\nTesting PredictiveAnalysisTool...")

    try:
        from agent_v3.tools.predictive_analysis import PredictiveAnalysisTool

        pred_tool = PredictiveAnalysisTool()
        print(f"✓ PredictiveAnalysisTool initialized: {pred_tool.name}")

        # Check that agents are initialized
        assert hasattr(pred_tool, 'planner'), "Missing planner agent"
        assert hasattr(pred_tool, 'retriever'), "Missing retriever agent"
        assert hasattr(pred_tool, 'answerer'), "Missing answerer agent"
        assert hasattr(pred_tool, 'critic'), "Missing critic agent"

        print("✓ All sub-agents initialized in PredictiveAnalysisTool")
        return True

    except Exception as e:
        print(f"✗ PredictiveAnalysisTool test failed: {e}")
        return False

def test_tool_registry():
    """Test that all tools are registered correctly"""
    print("\nTesting tool registry...")

    try:
        from agent_v3.tools import get_all_tools

        tools = get_all_tools()

        expected_new_tools = [
            "web_search",
            "clinical_context_search",
            "pharmaceutical_feature_engineering",
            "predictive_analysis"
        ]

        for tool_name in expected_new_tools:
            if tool_name in tools:
                print(f"✓ {tool_name} registered in tool registry")
            else:
                print(f"✗ {tool_name} NOT found in tool registry")
                return False

        print(f"✓ Total tools in registry: {len(tools)}")
        return True

    except Exception as e:
        print(f"✗ Tool registry test failed: {e}")
        return False

def test_orchestrator_multi_agent_detection():
    """Test that orchestrator can detect multi-agent workflow requirements"""
    print("\nTesting orchestrator multi-agent detection...")

    try:
        from agent_v3.orchestrator import RecursiveOrchestrator

        orchestrator = RecursiveOrchestrator("test_session", debug=False)

        # Test detection method
        test_queries = [
            ("Identify early prescribing signals", True),
            ("Predict high prescribers in Month 12", True),
            ("What features predict outcomes", True),
            ("Find prescribers of HUMIRA", False),
            ("List all doctors in California", False)
        ]

        for query, expected_result in test_queries:
            result = orchestrator._is_predictive_analysis_query(query)
            status = "✓" if result == expected_result else "✗"
            print(f"{status} Query: '{query[:40]}...' -> Detected as predictive: {result}")

            if result != expected_result:
                return False

        print("✓ Multi-agent workflow detection working correctly")
        return True

    except Exception as e:
        print(f"✗ Orchestrator multi-agent detection test failed: {e}")
        return False

def test_bigquery_credentials():
    """Test that BigQuery credentials are updated"""
    print("\nTesting BigQuery credentials configuration...")

    try:
        gcp_creds = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

        if not gcp_creds:
            print("✗ GOOGLE_APPLICATION_CREDENTIALS not set")
            return False

        if "e6b9f80f629a" in gcp_creds:
            print(f"✓ Using new BigQuery credentials: {gcp_creds}")
            return True
        elif "7fc568e0f2a7" in gcp_creds:
            print(f"✗ Still using old BigQuery credentials: {gcp_creds}")
            return False
        else:
            print(f"⚠️  Unknown credentials file: {gcp_creds}")
            return True  # Don't fail on unknown but valid path

    except Exception as e:
        print(f"✗ BigQuery credentials test failed: {e}")
        return False

def main():
    """Run all integration tests"""
    print("=" * 70)
    print("TAVILY, CRITIC AGENT & MULTI-AGENT WORKFLOW INTEGRATION TESTS")
    print("=" * 70)

    tests = [
        ("Configuration", [
            test_tavily_configuration,
            test_bigquery_credentials
        ]),
        ("Component Imports", [
            test_tavily_tool_import,
            test_critic_agent_import,
            test_pharmaceutical_features
        ]),
        ("Initialization", [
            test_tavily_tool_initialization,
            test_critic_agent_initialization,
            test_multi_agent_workflow_components,
            test_predictive_analysis_tool
        ]),
        ("Integration", [
            test_context_enhancements,
            test_tool_registry,
            test_orchestrator_multi_agent_detection
        ])
    ]

    total_passed = 0
    total_tests = 0

    for category, test_funcs in tests:
        print(f"\n{'='*70}")
        print(f"CATEGORY: {category}")
        print("=" * 70)

        for test_func in test_funcs:
            total_tests += 1
            try:
                if test_func():
                    total_passed += 1
                else:
                    print(f"⚠️  Test {test_func.__name__} failed")
            except Exception as e:
                print(f"✗ Test {test_func.__name__} crashed: {e}")

    print("\n" + "=" * 70)
    print(f"TEST SUMMARY: {total_passed}/{total_tests} tests passed")
    print("=" * 70)

    if total_passed == total_tests:
        print("🎉 All integration tests passed!")
        print("\n✅ System is ready for:")
        print("   • Tavily-powered web search")
        print("   • Critic agent quality assurance")
        print("   • Multi-agent predictive workflows")
        print("   • Pharmaceutical-specific feature engineering")
        print("   • NBRx, momentum, persistence, and access features")
        return True
    else:
        print(f"\n⚠️  {total_tests - total_passed} test(s) failed")
        print("Please review the issues above before running the agent")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
