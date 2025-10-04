"""
Test script for pharmaceutical feature engineering
"""
import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_pharmaceutical_features():
    """Test pharmaceutical feature engineering with sample data"""
    print("Testing pharmaceutical feature engineering...")

    try:
        from agent_v3.tools.pharmaceutical_features import PharmaceuticalFeatureEngineeringTool
        from agent_v3.context import Context
        import polars as pl
        from datetime import datetime, timedelta

        # Create test context
        context = Context("pharma_test")

        # Create sample pharmaceutical data
        base_date = datetime(2024, 1, 1)
        test_data = []

        # Create realistic pharmaceutical prescription data
        prescribers = [1234567890, 1234567891, 1234567892]
        drugs = ["Adalimumab", "Dupilumab", "Ustekinumab"]

        for i, prescriber in enumerate(prescribers):
            for j, drug in enumerate(drugs):
                # Create multiple prescriptions over time for each prescriber-drug combo
                for month in range(1, 13):  # 12 months of data
                    for script in range(1, 4):  # 1-3 scripts per month
                        script_date = base_date + timedelta(days=30*month + script*5)
                        test_data.append({
                            "PRESCRIBER_NPI_NBR": prescriber,
                            "NDC_DRUG_NM": drug,
                            "SERVICE_DATE_DD": script_date.strftime("%Y-%m-%d"),
                            "DISPENSED_QUANTITY_VAL": 2.0 * (i + 1),  # Varying quantities
                            "DAYS_SUPPLY_VAL": 28,
                            "TOTAL_PAID_AMT": 5000.0 + (i * 1000) + (j * 500),
                            "months_ago": 12 - month + 1
                        })

        # Convert to Polars DataFrame
        test_df = pl.DataFrame(test_data)
        print(f"✓ Created test dataset with {len(test_df)} records")

        # Add to context
        context.add_dataset("test_pharma_data", test_df)

        # Initialize pharmaceutical features tool
        pharma_tool = PharmaceuticalFeatureEngineeringTool()

        # Test feature engineering
        params = {
            "dataset_name": "test_pharma_data",
            "target_month": 12,
            "early_window": 3,
            "feature_set": "comprehensive"
        }

        result = pharma_tool.safe_execute(params, context)

        if "error" in result:
            print(f"✗ Pharmaceutical feature engineering failed: {result['error']}")
            return False
        else:
            print(f"✓ Pharmaceutical feature engineering successful")
            print(f"  Features dataset: {result.get('features_dataset', 'N/A')}")
            print(f"  Feature count: {result.get('feature_count', 'N/A')}")
            print(f"  Prescriber count: {result.get('prescriber_count', 'N/A')}")

            # Check if features were created
            features_dataset = result.get("features_dataset")
            if features_dataset and features_dataset in context.get_all_datasets():
                features_df = context.get_all_datasets()[features_dataset]
                print(f"  Features DataFrame shape: {features_df.shape}")
                print(f"  Feature columns: {features_df.columns[:10]}...")  # First 10 columns
                return True
            else:
                print("✗ Features dataset not found in context")
                return False

    except Exception as e:
        print(f"✗ Pharmaceutical features test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_multi_agent_workflow():
    """Test if multi-agent workflow works now"""
    print("\nTesting multi-agent workflow...")

    try:
        from agent_v3.tools.predictive_analysis import PredictiveAnalysisTool
        from agent_v3.context import Context

        # Create test context
        context = Context("multi_agent_test")

        # Initialize predictive analysis tool
        pred_tool = PredictiveAnalysisTool()

        # Test planning-only workflow (shouldn't fail on context issues)
        params = {
            "query": "Test predictive analysis for pharmaceutical features",
            "workflow_type": "planning_only",
            "validation_level": "basic"
        }

        result = pred_tool.safe_execute(params, context)

        if "error" in result:
            print(f"✗ Multi-agent workflow test failed: {result['error']}")
            return False
        else:
            print(f"✓ Multi-agent workflow test successful")
            print(f"  Stages completed: {result.get('stages_completed', [])}")
            return True

    except Exception as e:
        print(f"✗ Multi-agent workflow test failed: {e}")
        return False

def main():
    """Run tests"""
    print("=" * 60)
    print("PHARMACEUTICAL FEATURE ENGINEERING TESTS")
    print("=" * 60)

    tests_passed = 0
    total_tests = 2

    # Test pharmaceutical features
    if test_pharmaceutical_features():
        tests_passed += 1

    # Test multi-agent workflow
    if test_multi_agent_workflow():
        tests_passed += 1

    print("\n" + "=" * 60)
    print(f"TEST SUMMARY: {tests_passed}/{total_tests} tests passed")
    print("=" * 60)

    if tests_passed == total_tests:
        print("🎉 All tests passed! Pharmaceutical workflow improvements are working.")
        return True
    else:
        print(f"⚠️  {total_tests - tests_passed} test(s) failed. Check issues above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)