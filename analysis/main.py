#!/usr/bin/env python
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dynamic_query_processor import DynamicQueryProcessor
import warnings
warnings.filterwarnings('ignore')
import json


def print_header():
    print("\n" + "="*70)
    print("PHARMACEUTICAL ANALYTICS SYSTEM")
    print("="*70)
    print("\nType your query or 'quit' to exit.\n")


def format_results(results: dict):
    if results.get("insights"):
        print(f"\nINSIGHTS:")
        print("-"*60)
        print(results['insights'])
    
    if results.get("technical_data"):
        print(f"\n\nTECHNICAL DATA (Evidence/Proof):")
        print("-"*60)
        
        tech_data = results['technical_data']
        
        # Data Quality Indicators
        if 'data_quality' in tech_data:
            print(f"\nData Quality:")
            for key, value in tech_data['data_quality'].items():
                print(f"  • {key}: {value}")
        
        # Statistical Evidence
        if 'statistical_evidence' in tech_data:
            print(f"\nStatistical Evidence:")
            for test_name, test_data in tech_data['statistical_evidence'].items():
                if isinstance(test_data, dict):
                    print(f"  • {test_name}:")
                    print(f"    - p-value: {test_data.get('value', 'N/A')}")
                    print(f"    - {test_data.get('interpretation', '')}")
        
        # Key Metrics
        if 'key_metrics' in tech_data:
            print(f"\nKey Metrics:")
            for metric_name, metric_value in tech_data['key_metrics'].items():
                if isinstance(metric_value, (int, float)):
                    print(f"  • {metric_name}: {metric_value:,.2f}")
                elif isinstance(metric_value, dict):
                    print(f"  • {metric_name}: {metric_value}")
        
        # Methodology
        if 'methodology' in tech_data:
            print(f"\nMethodology: {tech_data['methodology']}")
        
        # Statistical Tests Performed
        if 'statistical_tests_performed' in tech_data:
            print(f"\nStatistical Tests:")
            for test in tech_data['statistical_tests_performed']:
                print(f"  • {test}")
        
        # Comparative Analysis
        if 'comparative_analysis' in tech_data:
            print(f"\nComparative Analysis:")
            print(f"  {tech_data['comparative_analysis']}")
    
    if results.get("results"):
        print(f"\n\nRESULTS SUMMARY:")
        print("-"*60)
        
        res = results['results']
        if 'summary_statistics' in res:
            for key, value in res['summary_statistics'].items():
                print(f"  • {key}: {value}")
    
    if results.get("visualizations"):
        print(f"\n\nVISUALIZATIONS:")
        print("-"*60)
        for viz in results['visualizations']:
            print(f"  ✓ {viz}")
    
    
    if results.get("datasets_used"):
        print(f"Datasets Used: {', '.join(results['datasets_used'])}")
    
    print("="*70)


def main():
    print_header()
    
    print("Initializing system...")
    
    try:
        processor = DynamicQueryProcessor()
        print("Ready!\n")
    except Exception as e:
        print(f"Error initializing system: {str(e)}")
        return
    
    while True:
        try:
            query = input("Query: ").strip()
            
            if query.lower() in ['quit', 'exit', 'q']:
                print("\nGoodbye!")
                break
            elif not query:
                continue
            
            print("\n" + "="*70)
            results = processor.process(query)
            format_results(results)
            
        except KeyboardInterrupt:
            print("\n\nGoodbye!")
            break
        except EOFError:
            print("\nError: EOF when reading a line")
        except Exception as e:
            print(f"\nError processing query: {str(e)}")


if __name__ == "__main__":
    main()