import pandas as pd
import os
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)

class DataLoader:
    """Centralized service to load all CSV data"""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        self._cache = {}
    
    def load_mock_ad_performance(self) -> pd.DataFrame:
        """Load mock ad performance data (100 ads)"""
        if 'mock_ads' not in self._cache:
            path = os.path.join(self.data_dir, "mock_ad_performance_data.csv")
            self._cache['mock_ads'] = pd.read_csv(path)
        return self._cache['mock_ads']
    
    def load_ad_metrics(self) -> pd.DataFrame:
        """Load detailed ad performance metrics (50 ads)"""
        if 'ad_metrics' not in self._cache:
            path = os.path.join(self.data_dir, "ad_performance_metrics.csv")
            self._cache['ad_metrics'] = pd.read_csv(path)
        return self._cache['ad_metrics']
    
    def load_ai_vs_traditional(self) -> pd.DataFrame:
        """Load AI vs Traditional comparison"""
        if 'comparison' not in self._cache:
            path = os.path.join(self.data_dir, "ai_vs_traditional_comparison.csv")
            self._cache['comparison'] = pd.read_csv(path)
        return self._cache['comparison']
    
    def load_cost_analysis(self) -> pd.DataFrame:
        """Load cost breakdown"""
        if 'costs' not in self._cache:
            path = os.path.join(self.data_dir, "cost_analysis.csv")
            self._cache['costs'] = pd.read_csv(path)
        return self._cache['costs']
    
    def load_competitive_matrix(self) -> pd.DataFrame:
        """Load competitive comparison"""
        if 'competitive' not in self._cache:
            path = os.path.join(self.data_dir, "competitive_comparison_matrix.csv")
            self._cache['competitive'] = pd.read_csv(path)
        return self._cache['competitive']
    
    def load_feature_adoption(self) -> pd.DataFrame:
        """Load feature adoption rates"""
        if 'features' not in self._cache:
            path = os.path.join(self.data_dir, "feature_adoption_rates.csv")
            self._cache['features'] = pd.read_csv(path)
        return self._cache['features']
    
    def load_performance_benchmarks(self) -> pd.DataFrame:
        """Load performance benchmarks"""
        if 'performance' not in self._cache:
            path = os.path.join(self.data_dir, "performance_benchmarks.csv")
            self._cache['performance'] = pd.read_csv(path)
        return self._cache['performance']
    
    def load_load_testing(self) -> pd.DataFrame:
        """Load load testing results"""
        if 'load_test' not in self._cache:
            path = os.path.join(self.data_dir, "load_testing_results.csv")
            self._cache['load_test'] = pd.read_csv(path)
        return self._cache['load_test']
    
    def get_analytics_summary(self) -> Dict:
        """Get comprehensive analytics summary"""
        mock_ads = self.load_mock_ad_performance()
        ad_metrics = self.load_ad_metrics()
        
        return {
            "total_ads": len(mock_ads) + len(ad_metrics),
            "total_views": int(mock_ads['Views'].sum() + ad_metrics['views'].sum()),
            "total_clicks": int(mock_ads['Clicks'].sum() + ad_metrics['clicks'].sum()),
            "total_conversions": int(mock_ads['Conversions'].sum() + ad_metrics['conversions'].sum()),
            "avg_ctr": round((mock_ads['CTR (%)'].mean() + ad_metrics['ctr'].mean()) / 2, 2),
            "avg_cvr": round((mock_ads['CVR (%)'].mean() + ad_metrics['conversion_rate'].mean()) / 2, 2),
            "avg_generation_time": round(mock_ads['Generation Time (s)'].mean(), 1),
            "platforms": list(mock_ads['Platform'].unique()),
            "products": list(set(list(mock_ads['Product'].unique()) + list(ad_metrics['product_type'].unique())))
        }

# Global instance
data_loader = DataLoader()
