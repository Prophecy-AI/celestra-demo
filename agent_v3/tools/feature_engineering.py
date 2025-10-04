"""
Feature engineering tool for predictive modeling in healthcare prescriber analysis
"""
import pandas as pd
import numpy as np
from typing import Dict, Any, List, Tuple
from datetime import datetime, timedelta
from .base import Tool, ToolResult


class FeatureEngineeringTool(Tool):
    """Tool for generating predictive features from early prescribing data"""

    def __init__(self):
        super().__init__(
            name="feature_engineering",
            description="Generate predictive features from Month 1-3 prescribing data"
        )

    def execute(self, parameters: Dict[str, Any], context: Any) -> ToolResult:
        """
        Generate predictive features from prescribing data

        Parameters:
        - dataset_name: Name of the dataset containing prescription data
        - target_month: Month to predict (default: 12)
        - feature_types: List of feature types to generate (default: ['volume', 'growth', 'consistency', 'behavioral'])
        - time_window: Early period in months (default: 3)
        """
        # Validate required parameters
        validation_error = self.validate_parameters(parameters, ["dataset_name"])
        if validation_error:
            return ToolResult(success=False, data={}, error=validation_error)

        dataset_name = parameters["dataset_name"]
        target_month = parameters.get("target_month", 12)
        feature_types = parameters.get("feature_types", ["volume", "growth", "consistency", "behavioral"])
        time_window = parameters.get("time_window", 3)

        try:
            # Get dataset from context
            datasets = context.get_all_datasets()
            if dataset_name not in datasets:
                return ToolResult(
                    success=False,
                    data={},
                    error=f"Dataset '{dataset_name}' not found in context"
                )

            df = datasets[dataset_name]

            # Generate features
            features_data = self._generate_predictive_features(
                df, target_month, feature_types, time_window
            )

            # Store engineered features as new dataset
            feature_dataset_name = f"{dataset_name}_features"
            context.add_dataset(feature_dataset_name, features_data["features_df"])

            return ToolResult(
                success=True,
                data={
                    "features_dataset": feature_dataset_name,
                    "feature_summary": features_data["summary"],
                    "feature_count": features_data["feature_count"],
                    "prescriber_count": len(features_data["features_df"]),
                    "message": f"Generated {features_data['feature_count']} features for {len(features_data['features_df'])} prescribers"
                }
            )

        except Exception as e:
            return ToolResult(
                success=False,
                data={},
                error=f"Feature engineering failed: {str(e)}"
            )

    def _generate_predictive_features(
        self,
        df: pd.DataFrame,
        target_month: int,
        feature_types: List[str],
        time_window: int
    ) -> Dict[str, Any]:
        """Generate comprehensive predictive features"""

        # Ensure we have the required columns
        required_columns = ['PRESCRIBER_NPI_NBR', 'SERVICE_DATE_DD', 'DISPENSED_QUANTITY_VAL']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            raise ValueError(f"Missing required columns: {missing_columns}")

        # Convert date column to datetime
        df['SERVICE_DATE_DD'] = pd.to_datetime(df['SERVICE_DATE_DD'])

        # Create month-year column for grouping
        df['month_year'] = df['SERVICE_DATE_DD'].dt.to_period('M')

        # Filter to early months (1-time_window)
        early_data = self._filter_early_months(df, time_window)

        # Initialize features dictionary
        all_features = {}
        feature_summary = {}

        # Generate different types of features
        if "volume" in feature_types:
            volume_features = self._generate_volume_features(early_data)
            all_features.update(volume_features)
            feature_summary["volume"] = len(volume_features)

        if "growth" in feature_types:
            growth_features = self._generate_growth_features(early_data)
            all_features.update(growth_features)
            feature_summary["growth"] = len(growth_features)

        if "consistency" in feature_types:
            consistency_features = self._generate_consistency_features(early_data)
            all_features.update(consistency_features)
            feature_summary["consistency"] = len(consistency_features)

        if "behavioral" in feature_types:
            behavioral_features = self._generate_behavioral_features(early_data)
            all_features.update(behavioral_features)
            feature_summary["behavioral"] = len(behavioral_features)

        # Convert to DataFrame
        features_df = pd.DataFrame(all_features).fillna(0)

        return {
            "features_df": features_df,
            "summary": feature_summary,
            "feature_count": len(features_df.columns)
        }

    def _filter_early_months(self, df: pd.DataFrame, time_window: int) -> pd.DataFrame:
        """Filter data to early months (1 to time_window)"""
        # Get the earliest date in the dataset
        min_date = df['SERVICE_DATE_DD'].min()

        # Calculate the cutoff date (time_window months from min_date)
        cutoff_date = min_date + pd.DateOffset(months=time_window)

        return df[df['SERVICE_DATE_DD'] < cutoff_date].copy()

    def _generate_volume_features(self, df: pd.DataFrame) -> Dict[str, List]:
        """Generate volume-based features"""
        features = {}

        # Group by prescriber
        prescriber_stats = df.groupby('PRESCRIBER_NPI_NBR').agg({
            'DISPENSED_QUANTITY_VAL': ['sum', 'mean', 'count', 'std'],
            'SERVICE_DATE_DD': ['nunique']
        }).round(2)

        prescriber_stats.columns = ['_'.join(col).strip() for col in prescriber_stats.columns]

        # Basic volume features
        features['total_volume'] = prescriber_stats['DISPENSED_QUANTITY_VAL_sum'].tolist()
        features['avg_volume_per_script'] = prescriber_stats['DISPENSED_QUANTITY_VAL_mean'].tolist()
        features['total_scripts'] = prescriber_stats['DISPENSED_QUANTITY_VAL_count'].tolist()
        features['volume_std'] = prescriber_stats['DISPENSED_QUANTITY_VAL_std'].fillna(0).tolist()
        features['active_days'] = prescriber_stats['SERVICE_DATE_DD_nunique'].tolist()

        # Volume intensity features
        features['scripts_per_active_day'] = (
            prescriber_stats['DISPENSED_QUANTITY_VAL_count'] /
            prescriber_stats['SERVICE_DATE_DD_nunique']
        ).fillna(0).round(2).tolist()

        # Volume percentiles (relative to all prescribers)
        features['volume_percentile'] = (
            prescriber_stats['DISPENSED_QUANTITY_VAL_sum'].rank(pct=True) * 100
        ).round(1).tolist()

        return features

    def _generate_growth_features(self, df: pd.DataFrame) -> Dict[str, List]:
        """Generate growth-based features"""
        features = {}

        # Monthly aggregations
        monthly_data = df.groupby(['PRESCRIBER_NPI_NBR', 'month_year']).agg({
            'DISPENSED_QUANTITY_VAL': 'sum'
        }).reset_index()

        # Calculate month-over-month growth
        monthly_data = monthly_data.sort_values(['PRESCRIBER_NPI_NBR', 'month_year'])
        monthly_data['prev_month_volume'] = monthly_data.groupby('PRESCRIBER_NPI_NBR')['DISPENSED_QUANTITY_VAL'].shift(1)
        monthly_data['mom_growth'] = (
            (monthly_data['DISPENSED_QUANTITY_VAL'] - monthly_data['prev_month_volume']) /
            monthly_data['prev_month_volume']
        ) * 100

        # Aggregate growth metrics by prescriber
        growth_stats = monthly_data.groupby('PRESCRIBER_NPI_NBR').agg({
            'mom_growth': ['mean', 'std', 'max', 'min']
        }).round(2)

        growth_stats.columns = ['_'.join(col).strip() for col in growth_stats.columns]

        features['avg_mom_growth'] = growth_stats['mom_growth_mean'].fillna(0).tolist()
        features['growth_volatility'] = growth_stats['mom_growth_std'].fillna(0).tolist()
        features['max_growth'] = growth_stats['mom_growth_max'].fillna(0).tolist()
        features['min_growth'] = growth_stats['mom_growth_min'].fillna(0).tolist()

        # Calculate CAGR (Compound Annual Growth Rate) approximation
        first_last_month = monthly_data.groupby('PRESCRIBER_NPI_NBR').agg({
            'DISPENSED_QUANTITY_VAL': ['first', 'last'],
            'month_year': ['count']
        })

        first_last_month.columns = ['_'.join(col).strip() for col in first_last_month.columns]

        cagr = (
            (first_last_month['DISPENSED_QUANTITY_VAL_last'] /
             first_last_month['DISPENSED_QUANTITY_VAL_first']) **
            (12 / first_last_month['month_year_count']) - 1
        ) * 100

        features['cagr_estimate'] = cagr.fillna(0).round(2).tolist()

        return features

    def _generate_consistency_features(self, df: pd.DataFrame) -> Dict[str, List]:
        """Generate consistency and volatility features"""
        features = {}

        # Weekly aggregations for more granular consistency
        df['week'] = df['SERVICE_DATE_DD'].dt.isocalendar().week
        df['year_week'] = df['SERVICE_DATE_DD'].dt.strftime('%Y-%U')

        weekly_data = df.groupby(['PRESCRIBER_NPI_NBR', 'year_week']).agg({
            'DISPENSED_QUANTITY_VAL': 'sum'
        }).reset_index()

        # Consistency metrics
        consistency_stats = weekly_data.groupby('PRESCRIBER_NPI_NBR').agg({
            'DISPENSED_QUANTITY_VAL': ['std', 'mean', 'count']
        }).round(2)

        consistency_stats.columns = ['_'.join(col).strip() for col in consistency_stats.columns]

        # Coefficient of variation (CV) - normalized volatility
        features['volume_cv'] = (
            consistency_stats['DISPENSED_QUANTITY_VAL_std'] /
            consistency_stats['DISPENSED_QUANTITY_VAL_mean']
        ).fillna(0).round(3).tolist()

        features['weekly_volume_std'] = consistency_stats['DISPENSED_QUANTITY_VAL_std'].fillna(0).tolist()
        features['active_weeks'] = consistency_stats['DISPENSED_QUANTITY_VAL_count'].tolist()

        # Calculate run lengths (consecutive periods with prescribing)
        run_lengths = self._calculate_run_lengths(weekly_data)
        features['max_run_length'] = run_lengths['max_run_length']
        features['avg_run_length'] = run_lengths['avg_run_length']

        return features

    def _generate_behavioral_features(self, df: pd.DataFrame) -> Dict[str, List]:
        """Generate behavioral pattern features"""
        features = {}

        # Drug diversity features
        if 'NDC_DRUG_NM' in df.columns:
            drug_diversity = df.groupby('PRESCRIBER_NPI_NBR')['NDC_DRUG_NM'].agg(['nunique', 'count'])
            features['unique_drugs'] = drug_diversity['nunique'].tolist()
            features['drug_concentration_ratio'] = (
                drug_diversity['nunique'] / drug_diversity['count']
            ).round(3).tolist()
        else:
            # Default values if drug names not available
            prescriber_list = df['PRESCRIBER_NPI_NBR'].unique().tolist()
            features['unique_drugs'] = [1] * len(prescriber_list)
            features['drug_concentration_ratio'] = [1.0] * len(prescriber_list)

        # Temporal patterns
        df['day_of_week'] = df['SERVICE_DATE_DD'].dt.dayofweek
        df['hour'] = df['SERVICE_DATE_DD'].dt.hour

        # Day of week preferences
        dow_stats = df.groupby('PRESCRIBER_NPI_NBR')['day_of_week'].agg(['mean', 'std'])
        features['preferred_dow'] = dow_stats['mean'].round(1).tolist()
        features['dow_variability'] = dow_stats['std'].fillna(0).round(2).tolist()

        # Patient load indicators (if available)
        if 'patient_id' in df.columns:
            patient_stats = df.groupby('PRESCRIBER_NPI_NBR')['patient_id'].nunique()
            features['unique_patients'] = patient_stats.tolist()
        else:
            # Estimate based on script frequency
            script_freq = df.groupby('PRESCRIBER_NPI_NBR').size()
            features['estimated_patient_load'] = (script_freq / 2).round().astype(int).tolist()

        return features

    def _calculate_run_lengths(self, weekly_data: pd.DataFrame) -> Dict[str, List]:
        """Calculate consecutive prescribing run lengths"""
        run_lengths = {}
        max_runs = []
        avg_runs = []

        for prescriber in weekly_data['PRESCRIBER_NPI_NBR'].unique():
            prescriber_data = weekly_data[
                weekly_data['PRESCRIBER_NPI_NBR'] == prescriber
            ].sort_values('year_week')

            # Convert weeks to consecutive integers for run calculation
            weeks = pd.to_datetime(prescriber_data['year_week'] + '-1', format='%Y-%U-%w')
            week_numbers = ((weeks - weeks.min()).dt.days // 7).tolist()

            runs = []
            current_run = 1

            for i in range(1, len(week_numbers)):
                if week_numbers[i] - week_numbers[i-1] == 1:
                    current_run += 1
                else:
                    runs.append(current_run)
                    current_run = 1

            if week_numbers:  # Add the last run
                runs.append(current_run)

            max_runs.append(max(runs) if runs else 1)
            avg_runs.append(np.mean(runs) if runs else 1)

        return {
            'max_run_length': max_runs,
            'avg_run_length': [round(x, 1) for x in avg_runs]
        }


class TrajectoryClassificationTool(Tool):
    """Tool for classifying mini-trajectory patterns"""

    def __init__(self):
        super().__init__(
            name="trajectory_classification",
            description="Classify prescriber trajectories into pattern categories"
        )

    def execute(self, parameters: Dict[str, Any], context: Any) -> ToolResult:
        """
        Classify prescriber trajectories

        Parameters:
        - features_dataset: Name of the features dataset
        - trajectory_types: List of trajectory types to identify
        """
        # Validate required parameters
        validation_error = self.validate_parameters(parameters, ["features_dataset"])
        if validation_error:
            return ToolResult(success=False, data={}, error=validation_error)

        features_dataset = parameters["features_dataset"]
        trajectory_types = parameters.get("trajectory_types", [
            "steady", "slow_start", "fast_launch", "volatile", "flat"
        ])

        try:
            # Get features dataset from context
            datasets = context.get_all_datasets()
            if features_dataset not in datasets:
                return ToolResult(
                    success=False,
                    data={},
                    error=f"Features dataset '{features_dataset}' not found in context"
                )

            features_df = datasets[features_dataset]

            # Classify trajectories
            trajectory_results = self._classify_trajectories(features_df, trajectory_types)

            # Store results
            trajectory_dataset_name = f"{features_dataset}_trajectories"
            context.add_dataset(trajectory_dataset_name, trajectory_results["trajectory_df"])

            return ToolResult(
                success=True,
                data={
                    "trajectory_dataset": trajectory_dataset_name,
                    "trajectory_distribution": trajectory_results["distribution"],
                    "classification_rules": trajectory_results["rules"],
                    "message": f"Classified {len(trajectory_results['trajectory_df'])} prescribers into trajectory patterns"
                }
            )

        except Exception as e:
            return ToolResult(
                success=False,
                data={},
                error=f"Trajectory classification failed: {str(e)}"
            )

    def _classify_trajectories(self, features_df: pd.DataFrame, trajectory_types: List[str]) -> Dict[str, Any]:
        """Classify prescribers into trajectory patterns"""

        trajectory_df = features_df.copy()

        # Define classification rules
        rules = {
            "steady": "Low growth volatility, consistent volume",
            "slow_start": "Low initial volume, positive growth trend",
            "fast_launch": "High initial growth, high volume",
            "volatile": "High growth volatility, inconsistent patterns",
            "flat": "Minimal growth, low volume"
        }

        # Initialize trajectory classification
        trajectory_df['trajectory_class'] = 'unclassified'

        # Classification logic based on features
        if all(col in features_df.columns for col in ['growth_volatility', 'avg_mom_growth', 'total_volume', 'volume_cv']):

            # Calculate percentiles for thresholds
            vol_50 = features_df['total_volume'].quantile(0.5)
            growth_vol_50 = features_df['growth_volatility'].quantile(0.5)
            growth_mean_pos = features_df['avg_mom_growth'] > 5  # 5% growth threshold
            cv_50 = features_df['volume_cv'].quantile(0.5)

            # Apply classification rules
            steady_mask = (
                (features_df['growth_volatility'] <= growth_vol_50) &
                (features_df['volume_cv'] <= cv_50) &
                (features_df['total_volume'] >= vol_50)
            )

            fast_launch_mask = (
                (features_df['avg_mom_growth'] > 20) &
                (features_df['total_volume'] >= vol_50)
            )

            volatile_mask = (
                (features_df['growth_volatility'] > growth_vol_50) &
                (features_df['volume_cv'] > cv_50)
            )

            slow_start_mask = (
                (features_df['total_volume'] < vol_50) &
                (features_df['avg_mom_growth'] > 0) &
                ~volatile_mask
            )

            flat_mask = (
                (features_df['total_volume'] < vol_50) &
                (features_df['avg_mom_growth'] <= 0)
            )

            # Apply classifications (order matters - most specific first)
            trajectory_df.loc[fast_launch_mask, 'trajectory_class'] = 'fast_launch'
            trajectory_df.loc[volatile_mask & ~fast_launch_mask, 'trajectory_class'] = 'volatile'
            trajectory_df.loc[steady_mask & ~fast_launch_mask & ~volatile_mask, 'trajectory_class'] = 'steady'
            trajectory_df.loc[slow_start_mask & ~fast_launch_mask & ~volatile_mask & ~steady_mask, 'trajectory_class'] = 'slow_start'
            trajectory_df.loc[flat_mask & ~fast_launch_mask & ~volatile_mask & ~steady_mask & ~slow_start_mask, 'trajectory_class'] = 'flat'

        # Calculate distribution
        distribution = trajectory_df['trajectory_class'].value_counts().to_dict()

        return {
            "trajectory_df": trajectory_df,
            "distribution": distribution,
            "rules": rules
        }