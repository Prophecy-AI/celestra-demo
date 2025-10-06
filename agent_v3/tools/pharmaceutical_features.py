"""
Pharmaceutical-specific feature engineering for prescriber prediction
"""
import polars as pl
import numpy as np
from typing import Dict, Any, List, Tuple
from .base import Tool, ToolResult


class PharmaceuticalFeatureEngineeringTool(Tool):
    """Tool for generating pharmaceutical-specific predictive features"""

    def __init__(self):
        super().__init__(
            name="pharmaceutical_feature_engineering",
            description="Generate pharmaceutical-specific predictive features for prescriber analysis"
        )

    def execute(self, parameters: Dict[str, Any], context: Any) -> ToolResult:
        """
        Generate pharmaceutical-specific features

        Parameters:
        - dataset_name: Name of the dataset containing prescription data
        - target_month: Month to predict (default: 12)
        - early_window: Early period in months (default: 3)
        - feature_set: Set of features to generate (default: 'comprehensive')
        """
        # Validate required parameters
        validation_error = self.validate_parameters(parameters, ["dataset_name"])
        if validation_error:
            return ToolResult(success=False, data={}, error=validation_error)

        dataset_name = parameters["dataset_name"]
        target_month = parameters.get("target_month", 12)
        early_window = parameters.get("early_window", 3)
        feature_set = parameters.get("feature_set", "comprehensive")

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

            # Generate pharmaceutical features
            features_data = self._generate_pharmaceutical_features(
                df, target_month, early_window, feature_set
            )

            # Store engineered features as new dataset
            feature_dataset_name = f"{dataset_name}_pharma_features"
            context.add_dataset(feature_dataset_name, features_data["features_df"])

            return ToolResult(
                success=True,
                data={
                    "features_dataset": feature_dataset_name,
                    "feature_summary": features_data["summary"],
                    "feature_count": features_data["feature_count"],
                    "prescriber_count": len(features_data["features_df"]),
                    "message": f"Generated {features_data['feature_count']} pharmaceutical features for {len(features_data['features_df'])} prescribers"
                }
            )

        except Exception as e:
            return ToolResult(
                success=False,
                data={},
                error=f"Pharmaceutical feature engineering failed: {str(e)}"
            )

    def _generate_pharmaceutical_features(
        self,
        df: pl.DataFrame,
        target_month: int,
        early_window: int,
        feature_set: str
    ) -> Dict[str, Any]:
        """Generate comprehensive pharmaceutical features"""

        # Ensure we have the required columns for pharmaceutical analysis
        required_columns = ['PRESCRIBER_NPI_NBR', 'NDC_DRUG_NM', 'SERVICE_DATE_DD', 'DISPENSED_QUANTITY_VAL']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            raise ValueError(f"Missing required columns: {missing_columns}")

        # Convert service date to datetime and add time-based columns
        # Handle both STRING and DATE types for SERVICE_DATE_DD
        if df.schema["SERVICE_DATE_DD"] == pl.String:
            df = df.with_columns([
                pl.col("SERVICE_DATE_DD").str.to_date().alias("service_date"),
                pl.col("DISPENSED_QUANTITY_VAL").cast(pl.Float64).alias("quantity")
            ])
        else:
            # Already a DATE type, just alias it
            df = df.with_columns([
                pl.col("SERVICE_DATE_DD").alias("service_date"),
                pl.col("DISPENSED_QUANTITY_VAL").cast(pl.Float64).alias("quantity")
            ])

        # Filter to early months (1-early_window) for feature engineering
        early_data = self._filter_to_early_months(df, early_window)

        # Initialize features dictionary
        all_features = {}
        feature_summary = {}

        # Generate feature sets based on pharmaceutical domain knowledge
        if feature_set in ["comprehensive", "nbrx"]:
            nbrx_features = self._generate_nbrx_features(early_data)
            all_features.update(nbrx_features)
            feature_summary["nbrx_features"] = len(nbrx_features)

        if feature_set in ["comprehensive", "momentum"]:
            momentum_features = self._generate_momentum_features(early_data)
            all_features.update(momentum_features)
            feature_summary["momentum_features"] = len(momentum_features)

        if feature_set in ["comprehensive", "persistence"]:
            persistence_features = self._generate_persistence_features(early_data)
            all_features.update(persistence_features)
            feature_summary["persistence_features"] = len(persistence_features)

        if feature_set in ["comprehensive", "access"]:
            access_features = self._generate_access_features(early_data)
            all_features.update(access_features)
            feature_summary["access_features"] = len(access_features)

        # Convert to DataFrame
        if all_features:
            # Get all prescriber NPIs to ensure consistent indexing
            all_prescribers = early_data.select("PRESCRIBER_NPI_NBR").unique().to_pandas()["PRESCRIBER_NPI_NBR"].tolist()

            # Create features DataFrame with proper indexing
            feature_rows = []
            for npi in all_prescribers:
                row = {"PRESCRIBER_NPI_NBR": npi}
                for feature_name, feature_values in all_features.items():
                    # Find the value for this prescriber or use default
                    if isinstance(feature_values, dict) and npi in feature_values:
                        row[feature_name] = feature_values[npi]
                    elif isinstance(feature_values, list) and len(feature_values) > 0:
                        # If it's a list, we need to match by position or use default
                        row[feature_name] = 0.0  # Default value
                    else:
                        row[feature_name] = 0.0
                feature_rows.append(row)

            features_df = pl.DataFrame(feature_rows)
        else:
            features_df = pl.DataFrame({"PRESCRIBER_NPI_NBR": early_data.select("PRESCRIBER_NPI_NBR").unique().to_pandas()["PRESCRIBER_NPI_NBR"].tolist()})

        return {
            "features_df": features_df,
            "summary": feature_summary,
            "feature_count": len(features_df.columns) - 1  # Exclude NPI column
        }

    def _filter_to_early_months(self, df: pl.DataFrame, early_window: int) -> pl.DataFrame:
        """Filter data to early months based on months_ago column or date"""

        if "months_ago" in df.columns:
            # Use months_ago column if available (preferred)
            max_months_ago = df.select(pl.col("months_ago").max()).item()
            early_threshold = max_months_ago - early_window + 1
            return df.filter(pl.col("months_ago") >= early_threshold)
        else:
            # Fall back to date-based filtering
            max_date = df.select(pl.col("service_date").max()).item()
            early_cutoff = max_date.replace(month=max(1, max_date.month - early_window + 1))
            return df.filter(pl.col("service_date") >= early_cutoff)

    def _generate_nbrx_features(self, df: pl.DataFrame) -> Dict[str, Any]:
        """Generate NBRx (New-to-Brand) count and share features"""
        features = {}

        # NBRx count per prescriber
        nbrx_counts = (
            df.group_by("PRESCRIBER_NPI_NBR")
            .agg([
                pl.col("quantity").sum().alias("total_nbrx_volume"),
                pl.col("NDC_DRUG_NM").n_unique().alias("unique_drugs_prescribed"),
                pl.len().alias("total_prescriptions")
            ])
        )

        # Convert to dictionary format for easier feature extraction
        nbrx_dict = nbrx_counts.to_pandas().set_index("PRESCRIBER_NPI_NBR").to_dict()

        features["total_nbrx_volume"] = nbrx_dict["total_nbrx_volume"]
        features["unique_drugs_prescribed"] = nbrx_dict["unique_drugs_prescribed"]
        features["total_prescriptions"] = nbrx_dict["total_prescriptions"]

        # Calculate NBRx share (simplified - would need therapeutic class data for full implementation)
        features["nbrx_concentration"] = {
            npi: nbrx_dict["unique_drugs_prescribed"][npi] / nbrx_dict["total_prescriptions"][npi]
            if nbrx_dict["total_prescriptions"][npi] > 0 else 0
            for npi in nbrx_dict["total_prescriptions"].keys()
        }

        return features

    def _generate_momentum_features(self, df: pl.DataFrame) -> Dict[str, Any]:
        """Generate momentum features (MoM growth and acceleration)"""
        features = {}

        # Group by prescriber and calculate monthly trends
        monthly_data = (
            df.with_columns([
                pl.col("service_date").dt.year().alias("year"),
                pl.col("service_date").dt.month().alias("month")
            ])
            .group_by(["PRESCRIBER_NPI_NBR", "year", "month"])
            .agg([
                pl.col("quantity").sum().alias("monthly_volume"),
                pl.len().alias("monthly_prescriptions")
            ])
            .sort(["PRESCRIBER_NPI_NBR", "year", "month"])
        )

        # Calculate month-over-month growth
        mom_growth_data = (
            monthly_data
            .with_columns([
                pl.col("monthly_volume").log().over("PRESCRIBER_NPI_NBR").alias("log_volume"),
                pl.col("monthly_prescriptions").log().over("PRESCRIBER_NPI_NBR").alias("log_prescriptions")
            ])
            .with_columns([
                (pl.col("log_volume") - pl.col("log_volume").shift(1).over("PRESCRIBER_NPI_NBR")).alias("mom_log_growth_volume"),
                (pl.col("log_prescriptions") - pl.col("log_prescriptions").shift(1).over("PRESCRIBER_NPI_NBR")).alias("mom_log_growth_prescriptions")
            ])
        )

        # Calculate acceleration (second derivative)
        acceleration_data = (
            mom_growth_data
            .with_columns([
                (pl.col("mom_log_growth_volume") - pl.col("mom_log_growth_volume").shift(1).over("PRESCRIBER_NPI_NBR")).alias("acceleration_volume"),
                (pl.col("mom_log_growth_prescriptions") - pl.col("mom_log_growth_prescriptions").shift(1).over("PRESCRIBER_NPI_NBR")).alias("acceleration_prescriptions")
            ])
        )

        # Aggregate momentum metrics by prescriber
        momentum_summary = (
            acceleration_data
            .group_by("PRESCRIBER_NPI_NBR")
            .agg([
                pl.col("mom_log_growth_volume").mean().alias("avg_mom_growth_volume"),
                pl.col("mom_log_growth_prescriptions").mean().alias("avg_mom_growth_prescriptions"),
                pl.col("acceleration_volume").mean().alias("avg_acceleration_volume"),
                pl.col("acceleration_prescriptions").mean().alias("avg_acceleration_prescriptions"),
                pl.col("mom_log_growth_volume").std().alias("momentum_volatility_volume")
            ])
            .fill_null(0)
        )

        # Convert to dictionary format
        momentum_dict = momentum_summary.to_pandas().set_index("PRESCRIBER_NPI_NBR").to_dict()

        features["avg_mom_growth_volume"] = momentum_dict["avg_mom_growth_volume"]
        features["avg_mom_growth_prescriptions"] = momentum_dict["avg_mom_growth_prescriptions"]
        features["avg_acceleration_volume"] = momentum_dict["avg_acceleration_volume"]
        features["avg_acceleration_prescriptions"] = momentum_dict["avg_acceleration_prescriptions"]
        features["momentum_volatility"] = momentum_dict["momentum_volatility_volume"]

        return features

    def _generate_persistence_features(self, df: pl.DataFrame) -> Dict[str, Any]:
        """Generate early persistence and refill timing features"""
        features = {}

        # Calculate time-to-first-refill and persistence metrics
        prescriber_drug_refills = (
            df.group_by(["PRESCRIBER_NPI_NBR", "NDC_DRUG_NM"])
            .agg([
                pl.col("service_date").min().alias("first_fill_date"),
                pl.col("service_date").max().alias("last_fill_date"),
                pl.col("service_date").count().alias("total_fills"),
                pl.col("service_date").sort().alias("fill_dates_sorted")
            ])
            .with_columns([
                (pl.col("last_fill_date") - pl.col("first_fill_date")).dt.total_days().alias("days_between_first_last"),
                (pl.col("total_fills") > 1).alias("has_refill")
            ])
        )

        # Calculate refill patterns per prescriber
        persistence_summary = (
            prescriber_drug_refills
            .group_by("PRESCRIBER_NPI_NBR")
            .agg([
                pl.col("has_refill").mean().alias("refill_rate"),
                pl.col("days_between_first_last").filter(pl.col("has_refill")).mean().alias("avg_time_to_refill"),
                pl.col("days_between_first_last").filter(pl.col("has_refill")).median().alias("median_time_to_refill"),
                pl.col("total_fills").mean().alias("avg_fills_per_drug")
            ])
            .fill_null(0)
        )

        # Convert to dictionary format
        persistence_dict = persistence_summary.to_pandas().set_index("PRESCRIBER_NPI_NBR").to_dict()

        features["early_refill_rate"] = persistence_dict["refill_rate"]
        features["avg_time_to_refill"] = persistence_dict["avg_time_to_refill"]
        features["median_time_to_refill"] = persistence_dict["median_time_to_refill"]
        features["avg_fills_per_drug"] = persistence_dict["avg_fills_per_drug"]

        return features

    def _generate_access_features(self, df: pl.DataFrame) -> Dict[str, Any]:
        """Generate access and adherence proxy features"""
        features = {}

        # OOP burden features (using TOTAL_PAID_AMT as proxy)
        if "TOTAL_PAID_AMT" in df.columns:
            oop_features = (
                df.filter(pl.col("TOTAL_PAID_AMT").is_not_null())
                .group_by("PRESCRIBER_NPI_NBR")
                .agg([
                    pl.col("TOTAL_PAID_AMT").median().alias("median_oop_cost"),
                    pl.col("TOTAL_PAID_AMT").mean().alias("avg_oop_cost"),
                    pl.col("TOTAL_PAID_AMT").std().alias("oop_cost_variability")
                ])
                .fill_null(0)
            )

            oop_dict = oop_features.to_pandas().set_index("PRESCRIBER_NPI_NBR").to_dict()
            features["median_oop_burden"] = oop_dict["median_oop_cost"]
            features["avg_oop_burden"] = oop_dict["avg_oop_cost"]
            features["oop_cost_variability"] = oop_dict["oop_cost_variability"]

        # Days supply consistency (as adherence proxy)
        if "DAYS_SUPPLY_VAL" in df.columns:
            adherence_features = (
                df.filter(pl.col("DAYS_SUPPLY_VAL").is_not_null())
                .group_by("PRESCRIBER_NPI_NBR")
                .agg([
                    pl.col("DAYS_SUPPLY_VAL").mean().alias("avg_days_supply"),
                    pl.col("DAYS_SUPPLY_VAL").std().alias("days_supply_consistency"),
                    (pl.col("DAYS_SUPPLY_VAL") >= 30).mean().alias("monthly_supply_rate")
                ])
                .fill_null(0)
            )

            adherence_dict = adherence_features.to_pandas().set_index("PRESCRIBER_NPI_NBR").to_dict()
            features["avg_days_supply"] = adherence_dict["avg_days_supply"]
            features["days_supply_consistency"] = adherence_dict["days_supply_consistency"]
            features["monthly_supply_rate"] = adherence_dict["monthly_supply_rate"]

        return features