import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Dict, List, Any, Optional
import warnings
warnings.filterwarnings('ignore')


class AnalyticsVisualizer:
    def __init__(self):
        sns.set_style('whitegrid')
        sns.set_palette('Set2')
        plt.rcParams['figure.figsize'] = (14, 8)
        plt.rcParams['font.size'] = 11
        plt.rcParams['font.family'] = 'sans-serif'
        plt.rcParams['axes.titlesize'] = 14
        plt.rcParams['axes.labelsize'] = 12
        
        # Images directory for all visualizations
        import os
        self.images_dir = 'images'
        if not os.path.exists(self.images_dir):
            os.makedirs(self.images_dir)
    
    def _get_image_path(self, filename: str) -> str:
        """Ensure filename is in images directory"""
        import os
        if not filename.startswith(self.images_dir):
            filename = os.path.join(self.images_dir, os.path.basename(filename))
        return filename
        
    def create_visualization(self, viz_type: str, data: Any, title: str, filename: str, **kwargs):
        if viz_type == 'bar_chart':
            self.create_bar_chart(data, title, filename, **kwargs)
        elif viz_type == 'heatmap':
            self.create_heatmap(data, title, filename, **kwargs)
        elif viz_type == 'line_chart':
            self.create_line_chart(data, title, filename, **kwargs)
        elif viz_type == 'scatter_plot':
            self.create_scatter_plot(data, title, filename, **kwargs)
        elif viz_type == 'pie_chart':
            self.create_pie_chart(data, title, filename, **kwargs)
        elif viz_type == 'stacked_bar':
            self.create_stacked_bar(data, title, filename, **kwargs)
        else:
            self.create_bar_chart(data, title, filename, **kwargs)
    
    def create_bar_chart(self, data: pd.DataFrame, title: str, filename: str, **kwargs):
        fig, ax = plt.subplots(figsize=(12, 8))
        
        if isinstance(data, pd.DataFrame):
            x_col = kwargs.get('x', data.columns[0])
            y_col = kwargs.get('y', data.columns[1])
            data_sorted = data.sort_values(y_col, ascending=False).head(15)
            
            colors = sns.color_palette('viridis', len(data_sorted))
            bars = ax.bar(range(len(data_sorted)), data_sorted[y_col], color=colors)
            ax.set_xticks(range(len(data_sorted)))
            ax.set_xticklabels(data_sorted[x_col], rotation=45, ha='right')
            ax.set_ylabel(kwargs.get('ylabel', y_col), fontweight='bold')
            
            for bar in bars:
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height,
                       f'{height:.1f}', ha='center', va='bottom')
        
        ax.set_title(title, fontsize=16, fontweight='bold', pad=20)
        ax.grid(axis='y', alpha=0.3)
        plt.tight_layout()
        plt.savefig(self._get_image_path(filename), dpi=150, bbox_inches='tight')
        plt.close()
    
    def create_heatmap(self, data: pd.DataFrame, title: str, filename: str, **kwargs):
        fig, ax = plt.subplots(figsize=(12, 10))
        
        if isinstance(data, pd.DataFrame):
            sns.heatmap(data, annot=True, fmt=kwargs.get('fmt', '.2f'), 
                       cmap=kwargs.get('cmap', 'RdYlGn'), 
                       cbar_kws={'label': kwargs.get('cbar_label', 'Value')},
                       ax=ax, linewidths=0.5, linecolor='gray')
        
        ax.set_title(title, fontsize=16, fontweight='bold', pad=20)
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')
        plt.tight_layout()
        plt.savefig(self._get_image_path(filename), dpi=150, bbox_inches='tight')
        plt.close()
    
    def create_line_chart(self, data: pd.DataFrame, title: str, filename: str, **kwargs):
        fig, ax = plt.subplots(figsize=(12, 8))
        
        if isinstance(data, pd.DataFrame):
            x_col = kwargs.get('x', data.columns[0])
            y_cols = kwargs.get('y', [col for col in data.columns if col != x_col])
            
            if not isinstance(y_cols, list):
                y_cols = [y_cols]
            
            for y_col in y_cols:
                ax.plot(data[x_col], data[y_col], marker='o', linewidth=2, 
                       markersize=6, label=y_col)
        
        ax.set_xlabel(kwargs.get('xlabel', x_col), fontweight='bold')
        ax.set_ylabel(kwargs.get('ylabel', 'Value'), fontweight='bold')
        ax.set_title(title, fontsize=16, fontweight='bold', pad=20)
        ax.grid(True, alpha=0.3)
        ax.legend()
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')
        plt.tight_layout()
        plt.savefig(self._get_image_path(filename), dpi=150, bbox_inches='tight')
        plt.close()
    
    def create_scatter_plot(self, data: pd.DataFrame, title: str, filename: str, **kwargs):
        fig, ax = plt.subplots(figsize=(12, 8))
        
        if isinstance(data, pd.DataFrame):
            x_col = kwargs.get('x', data.columns[0])
            y_col = kwargs.get('y', data.columns[1])
            size_col = kwargs.get('size', None)
            color_col = kwargs.get('color', None)
            
            scatter_kwargs = {'alpha': 0.6}
            if size_col and size_col in data.columns:
                scatter_kwargs['s'] = data[size_col]
            if color_col and color_col in data.columns:
                scatter_kwargs['c'] = data[color_col]
                scatter_kwargs['cmap'] = 'viridis'
            
            ax.scatter(data[x_col], data[y_col], **scatter_kwargs)
        
        ax.set_xlabel(kwargs.get('xlabel', x_col), fontweight='bold')
        ax.set_ylabel(kwargs.get('ylabel', y_col), fontweight='bold')
        ax.set_title(title, fontsize=16, fontweight='bold', pad=20)
        ax.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(self._get_image_path(filename), dpi=150, bbox_inches='tight')
        plt.close()
    
    def create_pie_chart(self, data: pd.DataFrame, title: str, filename: str, **kwargs):
        fig, ax = plt.subplots(figsize=(10, 10))
        
        if isinstance(data, pd.DataFrame) or isinstance(data, pd.Series):
            if isinstance(data, pd.DataFrame):
                values = data[kwargs.get('values', data.columns[-1])]
                labels = data[kwargs.get('labels', data.columns[0])]
            else:
                values = data.values
                labels = data.index
            
            # Limit to top 10 for readability
            if len(values) > 10:
                top_n = pd.Series(values, index=labels).nlargest(9)
                other_sum = pd.Series(values, index=labels).iloc[9:].sum()
                values = list(top_n.values) + [other_sum]
                labels = list(top_n.index) + ['Others']
            
            wedges, texts, autotexts = ax.pie(values, labels=labels, autopct='%1.1f%%',
                                              startangle=90, colors=sns.color_palette('Set3'))
        
        ax.set_title(title, fontsize=16, fontweight='bold', pad=20)
        plt.tight_layout()
        plt.savefig(self._get_image_path(filename), dpi=150, bbox_inches='tight')
        plt.close()
    
    def create_stacked_bar(self, data: pd.DataFrame, title: str, filename: str, **kwargs):
        fig, ax = plt.subplots(figsize=(12, 8))
        
        if isinstance(data, pd.DataFrame):
            data.plot(kind='bar', stacked=True, ax=ax, 
                     colormap=kwargs.get('colormap', 'viridis'))
        
        ax.set_xlabel(kwargs.get('xlabel', 'Category'), fontweight='bold')
        ax.set_ylabel(kwargs.get('ylabel', 'Value'), fontweight='bold')
        ax.set_title(title, fontsize=16, fontweight='bold', pad=20)
        ax.legend(title=kwargs.get('legend_title', 'Legend'), bbox_to_anchor=(1.05, 1), loc='upper left')
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')
        plt.tight_layout()
        plt.savefig(self._get_image_path(filename), dpi=150, bbox_inches='tight')
        plt.close()
    
    def create_feature_importance_visuals(self, importance_df: pd.DataFrame, title: str, filename: str):
        if importance_df is None or importance_df.empty:
            return
        
        fig = plt.figure(figsize=(16, 10))
        
        ax1 = plt.subplot(2, 1, 1)
        self.create_bar_chart(importance_df, f"{title} - Bar Chart", "temp.png", 
                             x='feature', y='importance', ylabel='Importance Score')
        plt.close()
        
        importance_df_sorted = importance_df.sort_values('importance', ascending=True)
        colors = sns.color_palette('RdYlGn', len(importance_df_sorted))
        bars = ax1.barh(importance_df_sorted['feature'], importance_df_sorted['importance'], color=colors)
        
        ax1.set_xlabel('Importance Score', fontsize=12, fontweight='bold')
        ax1.set_ylabel('Features', fontsize=12, fontweight='bold')
        ax1.set_title(title, fontsize=14, fontweight='bold', pad=20)
        ax1.grid(axis='x', alpha=0.3)
        
        for bar in bars:
            width = bar.get_width()
            ax1.text(width, bar.get_y() + bar.get_height()/2, 
                    f'{width:.3f}', ha='left', va='center', fontsize=10)
        
        ax2 = plt.subplot(2, 1, 2)
        importance_matrix = importance_df.set_index('feature')[['importance']].T
        sns.heatmap(importance_matrix, annot=True, fmt='.3f', cmap='RdYlGn',
                   cbar_kws={'label': 'Importance Score'}, ax=ax2,
                   linewidths=0.5, linecolor='gray')
        ax2.set_title('Feature Importance Heatmap', fontsize=14, fontweight='bold', pad=20)
        ax2.set_xlabel('')
        ax2.set_ylabel('')
        plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45, ha='right')
        
        plt.tight_layout()
        plt.savefig(self._get_image_path(filename), dpi=150, bbox_inches='tight')
        plt.close()
        print(f"Visualization saved: {filename}")
    
    def create_market_share_visuals(self, market_share_df: pd.DataFrame, filename: str):
        if market_share_df.empty:
            return
            
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        
        if 'NDC_PREFERRED_BRAND_NM' in market_share_df.columns:
            drug_share = market_share_df.groupby('NDC_PREFERRED_BRAND_NM')['prescription_market_share'].mean()
            drug_share = drug_share.sort_values(ascending=False).head(10)
            
            if not drug_share.empty:
                self.create_bar_chart(
                    pd.DataFrame({'Drug': drug_share.index, 'Market Share': drug_share.values}),
                    'Market Share by Drug', filename
                )
    
    def create_correlation_heatmap(self, correlation_matrix: pd.DataFrame, filename: str):
        if correlation_matrix.empty:
            return
        
        mask = np.triu(np.ones_like(correlation_matrix, dtype=bool))
        self.create_heatmap(correlation_matrix, 'Feature Correlation Analysis', filename,
                           cmap='coolwarm', fmt='.2f', cbar_label='Correlation')
    
    def create_geographic_visuals(self, state_df: pd.DataFrame, filename: str):
        if state_df.empty:
            return
            
        top_states = state_df.sort_values('claim_count', ascending=False).head(15)
        self.create_bar_chart(
            pd.DataFrame({'State': top_states['state'], 'Prescriptions': top_states['claim_count']}),
            'Top States by Prescription Volume', filename,
            ylabel='Prescription Count'
        )
    
    def create_segment_performance_visuals(self, segment_df: pd.DataFrame, filename: str):
        if segment_df.empty:
            return
            
        segment_df_sorted = segment_df.sort_values('total_volume', ascending=False).head(10)
        self.create_bar_chart(
            pd.DataFrame({
                'Segment': segment_df_sorted['PRESCRIBER_NPI_HCP_SEGMENT_DESC'],
                'Volume': segment_df_sorted['total_volume']
            }),
            'Top Segments by Volume', filename,
            ylabel='Total Volume'
        )
    
    def create_prescriber_behavior_visuals(self, prescriber_df: pd.DataFrame, filename: str):
        if prescriber_df.empty:
            return
            
        if 'total_prescriptions' in prescriber_df.columns:
            top_prescribers = prescriber_df.sort_values('total_prescriptions', ascending=False).head(15)
            self.create_bar_chart(
                pd.DataFrame({
                    'Prescriber': [f"Prescriber {i+1}" for i in range(len(top_prescribers))],
                    'Prescriptions': top_prescribers['total_prescriptions'].values
                }),
                'Top Prescribers by Volume', filename,
                ylabel='Total Prescriptions'
            )
    
    def create_top_drugs_visual(self, drugs_df: pd.DataFrame, filename: str):
        if drugs_df.empty:
            return
            
        self.create_bar_chart(
            pd.DataFrame({
                'Drug': drugs_df['drug_name'],
                'Prescriptions': drugs_df['prescription_count']
            }),
            'Top Drugs by Prescription Volume', filename,
            ylabel='Prescription Count'
        )