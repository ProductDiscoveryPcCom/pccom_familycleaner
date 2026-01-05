"""
Analyzers Module - CORREGIDO
Lógica central de análisis UX + SEO con cruce de datos
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from .data_processor import DataProcessor, AnalysisResults


class FacetAnalyzer:
    """Analizador principal de facetas UX + SEO"""
    
    def __init__(self, processor: DataProcessor):
        self.processor = processor
        self.results = AnalysisResults()
    
    # ═══════════════════════════════════════════════════════════════════════════
    # ANÁLISIS DE USO DE FILTROS (UX - ENCONTRABILIDAD)
    # ═══════════════════════════════════════════════════════════════════════════
    
    def analyze_filter_usage(self, source: str = 'all') -> pd.DataFrame:
        """
        Analiza el uso de filtros desde Analytics
        Calcula: % de uso por tipo de faceta, orden óptimo
        """
        df_key = f'filter_usage_{source}'
        if df_key not in self.processor.data:
            return pd.DataFrame()
        
        df = self.processor.data[df_key].copy()
        
        # Excluir "total" y "sorting" (no son facetas navegables)
        df = df[~df['facet_type'].isin(['total', 'sorting', 'other'])]
        
        # Calcular totales por tipo de faceta
        total_sessions = df['sessions'].sum()
        
        facet_summary = df.groupby('facet_type').agg({
            'sessions': 'sum',
            'facet_value': 'count'
        }).reset_index()
        
        facet_summary.columns = ['facet_type', 'total_sessions', 'num_values']
        facet_summary['pct_usage'] = (facet_summary['total_sessions'] / total_sessions * 100).round(2)
        facet_summary = facet_summary.sort_values('total_sessions', ascending=False)
        
        # Guardar orden óptimo de facetas
        self.results.facet_priority_order = facet_summary['facet_type'].tolist()
        self.results.facet_usage = facet_summary
        
        return facet_summary
    
    def get_top_values_per_facet(self, source: str = 'all', top_n: int = 10) -> Dict[str, pd.DataFrame]:
        """Obtiene los top valores por cada tipo de faceta"""
        df_key = f'filter_usage_{source}'
        if df_key not in self.processor.data:
            return {}
        
        df = self.processor.data[df_key].copy()
        df = df[~df['facet_type'].isin(['total', 'sorting', 'other'])]
        
        result = {}
        for facet_type in df['facet_type'].unique():
            facet_df = df[df['facet_type'] == facet_type].nlargest(top_n, 'sessions')
            result[facet_type] = facet_df
        
        return result
    
    def detect_filters_to_noindex(self, source: str = 'all') -> pd.DataFrame:
        """
        Detecta filtros que NO deben indexarse:
        - Ordenación (order:*)
        - Precio (precio:*)
        """
        df_key = f'filter_usage_{source}'
        if df_key not in self.processor.data:
            return pd.DataFrame()
        
        df = self.processor.data[df_key].copy()
        
        noindex_types = ['sorting', 'price']
        noindex_df = df[df['facet_type'].isin(noindex_types)].copy()
        noindex_df['action'] = 'NOINDEX'
        noindex_df['reason'] = noindex_df['facet_type'].apply(
            lambda x: 'Ordenación - no genera URL única' if x == 'sorting' 
                     else 'Precio - usar AJAX sin URL'
        )
        
        return noindex_df
    
    # ═══════════════════════════════════════════════════════════════════════════
    # ANÁLISIS DE URLS (SEO - VISIBILIDAD)
    # ═══════════════════════════════════════════════════════════════════════════
    
    def analyze_url_distribution(self, top_query_df: pd.DataFrame = None) -> pd.DataFrame:
        """Analiza distribución de URLs por tipo y rendimiento"""
        if top_query_df is None:
            top_query_df = self.processor.data.get('top_query', pd.DataFrame())
        
        if top_query_df.empty:
            return pd.DataFrame()
        
        df = top_query_df.copy()
        
        # Clasificar URLs
        url_info = df['url'].apply(self.processor.classify_url)
        df['url_type'] = url_info.apply(lambda x: x['type'])
        df['num_facets'] = url_info.apply(lambda x: x['num_facets'])
        df['has_sorting'] = url_info.apply(lambda x: x['has_sorting'])
        df['has_pagination'] = url_info.apply(lambda x: x['has_pagination'])
        df['has_price'] = url_info.apply(lambda x: x['has_price'])
        
        # Extraer facetas individuales
        facets = url_info.apply(lambda x: x['facets'])
        df['facet_size'] = facets.apply(lambda x: x.get('size'))
        df['facet_brand'] = facets.apply(lambda x: x.get('brand'))
        df['facet_technology'] = facets.apply(lambda x: x.get('technology'))
        df['facet_connectivity'] = facets.apply(lambda x: x.get('connectivity'))
        
        # Clasificar intención de top query
        df['query_intent'] = df['top_query'].apply(self.processor.classify_query_intent)
        
        self.results.url_classification = df
        return df
    
    def detect_cannibalization(self, top_query_df: pd.DataFrame = None) -> pd.DataFrame:
        """
        Detecta canibalización: Artículos rankeando para queries transaccionales
        """
        df = self.analyze_url_distribution(top_query_df)
        
        if df.empty:
            return pd.DataFrame()
        
        # Canibalización = ARTICLE + TRANSACTIONAL query
        cannib = df[
            (df['url_type'] == 'ARTICLE') & 
            (df['query_intent'] == 'TRANSACTIONAL')
        ].copy()
        
        if cannib.empty:
            self.results.cannibalization = pd.DataFrame()
            return pd.DataFrame()
        
        # Añadir filtro sugerido
        cannib['suggested_filter'] = cannib['top_query'].apply(
            self.processor.suggest_filter_url
        )
        
        # Calcular impacto
        clicks_col = 'top_query_clicks' if 'top_query_clicks' in cannib.columns else 'clicks'
        cannib['impact_score'] = cannib[clicks_col].fillna(0)
        
        # Ordenar por impacto
        cannib = cannib.sort_values('impact_score', ascending=False)
        
        self.results.cannibalization = cannib
        return cannib
    
    def analyze_facet_performance(self, top_query_df: pd.DataFrame = None) -> pd.DataFrame:
        """Analiza rendimiento SEO de cada tipo de faceta"""
        df = self.analyze_url_distribution(top_query_df)
        
        if df.empty:
            return pd.DataFrame()
        
        # Solo filtros
        filters = df[df['url_type'] == 'FILTER'].copy()
        
        if filters.empty:
            return pd.DataFrame()
        
        clicks_col = 'clicks' if 'clicks' in filters.columns else 'url_total_clicks'
        position_col = 'position' if 'position' in filters.columns else 'url_avg_position'
        
        performance = []
        
        for facet_col, facet_name in [('facet_size', 'size'), 
                                       ('facet_brand', 'brand'),
                                       ('facet_technology', 'technology'),
                                       ('facet_connectivity', 'connectivity')]:
            if facet_col in filters.columns:
                perf = filters.groupby(facet_col).agg({
                    clicks_col: 'sum',
                    position_col: 'mean',
                    'url': 'count'
                }).reset_index()
                perf.columns = ['facet_value', 'total_clicks', 'avg_position', 'num_urls']
                perf['facet_type'] = facet_name
                perf = perf[perf['facet_value'].notna()]
                performance.append(perf)
        
        if not performance:
            return pd.DataFrame()
        
        result = pd.concat(performance, ignore_index=True)
        self.results.facet_performance = result
        return result
    
    # ═══════════════════════════════════════════════════════════════════════════
    # CRUCE UX + SEO (EL ANÁLISIS MÁS VALIOSO)
    # ═══════════════════════════════════════════════════════════════════════════
    
    def analyze_ux_seo_matrix(self) -> pd.DataFrame:
        """
        Cruza datos de uso interno (UX) con rendimiento SEO
        Detecta: 
        - Filtros con alta demanda SEO pero bajo uso interno
        - Filtros muy usados internamente pero sin visibilidad SEO
        """
        # Necesitamos ambos datasets
        usage_df = self.results.facet_usage
        perf_df = self.results.facet_performance
        
        if usage_df.empty or perf_df.empty:
            return pd.DataFrame()
        
        # Agregar performance por tipo de faceta
        seo_by_type = perf_df.groupby('facet_type').agg({
            'total_clicks': 'sum',
            'avg_position': 'mean',
            'num_urls': 'sum'
        }).reset_index()
        seo_by_type.columns = ['facet_type', 'seo_clicks', 'seo_avg_position', 'seo_urls']
        
        # Merge con usage
        matrix = usage_df.merge(seo_by_type, on='facet_type', how='outer')
        matrix = matrix.fillna(0)
        
        # Calcular métricas de análisis
        total_ux = matrix['total_sessions'].sum()
        total_seo = matrix['seo_clicks'].sum()
        
        if total_ux > 0:
            matrix['ux_share'] = (matrix['total_sessions'] / total_ux * 100).round(2)
        else:
            matrix['ux_share'] = 0
            
        if total_seo > 0:
            matrix['seo_share'] = (matrix['seo_clicks'] / total_seo * 100).round(2)
        else:
            matrix['seo_share'] = 0
        
        # Gap analysis
        matrix['ux_seo_gap'] = matrix['ux_share'] - matrix['seo_share']
        
        # Clasificar oportunidades
        def classify_opportunity(row):
            if row['ux_share'] > 10 and row['seo_share'] < 5:
                return '🔴 Alta UX, Baja SEO - Oportunidad de visibilidad'
            elif row['seo_share'] > 10 and row['ux_share'] < 5:
                return '🟡 Alta SEO, Baja UX - Revisar navegación'
            elif row['ux_share'] > 10 and row['seo_share'] > 10:
                return '✅ Equilibrado'
            else:
                return '⚪ Bajo impacto'
        
        matrix['opportunity'] = matrix.apply(classify_opportunity, axis=1)
        
        self.results.ux_seo_matrix = matrix
        return matrix
    
    def analyze_ux_seo_by_value(self, usage_source: str = 'all') -> pd.DataFrame:
        """
        Cruce granular: cada valor de faceta (ej: 55 pulgadas)
        UX: Sesiones de navegación
        SEO: Clics desde búsqueda
        """
        # Usage por valor
        df_key = f'filter_usage_{usage_source}'
        if df_key not in self.processor.data:
            return pd.DataFrame()
        
        usage = self.processor.data[df_key].copy()
        usage = usage[~usage['facet_type'].isin(['total', 'sorting', 'other', 'price'])]
        
        # Performance por valor
        perf = self.results.facet_performance
        if perf.empty:
            return pd.DataFrame()
        
        # Normalizar valores para hacer join
        usage['join_key'] = usage['facet_type'] + '_' + usage['facet_value'].astype(str).str.lower()
        perf['join_key'] = perf['facet_type'] + '_' + perf['facet_value'].astype(str).str.lower()
        
        # Merge
        matrix = usage.merge(
            perf[['join_key', 'total_clicks', 'avg_position', 'num_urls']],
            on='join_key',
            how='outer'
        )
        
        matrix = matrix.fillna(0)
        matrix = matrix.rename(columns={
            'sessions': 'ux_sessions',
            'total_clicks': 'seo_clicks'
        })
        
        # Calcular ratio
        matrix['seo_ux_ratio'] = np.where(
            matrix['ux_sessions'] > 0,
            matrix['seo_clicks'] / matrix['ux_sessions'],
            0
        )
        
        # Clasificar
        def classify_value(row):
            if row['ux_sessions'] > 1000 and row['seo_clicks'] < 100:
                return '🔴 Gap SEO crítico'
            elif row['seo_clicks'] > 500 and row['ux_sessions'] < 100:
                return '🟡 Sin soporte UX'
            elif row['ux_sessions'] > 500 and row['seo_clicks'] > 200:
                return '✅ Bien alineado'
            else:
                return '⚪ Bajo volumen'
        
        matrix['status'] = matrix.apply(classify_value, axis=1)
        
        return matrix.sort_values('ux_sessions', ascending=False)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # DETECCIÓN DE GAPS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def detect_gaps(self, keyword_df: pd.DataFrame = None, 
                   top_query_df: pd.DataFrame = None) -> pd.DataFrame:
        """
        Detecta gaps: Keywords con demanda pero sin filtro dedicado
        """
        if keyword_df is None:
            keyword_df = self.processor.data.get('keyword_research', pd.DataFrame())
        
        if keyword_df.empty:
            return pd.DataFrame()
        
        # Obtener URLs existentes
        url_df = self.analyze_url_distribution(top_query_df)
        existing_filters = set()
        if not url_df.empty:
            existing_filters = set(
                url_df[url_df['url_type'] == 'FILTER']['url']
                .str.lower()
                .tolist()
            )
        
        gaps = []
        keyword_col = 'keyword' if 'keyword' in keyword_df.columns else keyword_df.columns[0]
        volume_col = 'volume' if 'volume' in keyword_df.columns else None
        
        for _, row in keyword_df.iterrows():
            keyword = row.get(keyword_col, '')
            volume = row.get(volume_col, 0) if volume_col else 0
            
            if pd.isna(keyword):
                continue
            
            intent = self.processor.classify_query_intent(keyword)
            
            if intent != 'TRANSACTIONAL':
                continue
            
            suggested = self.processor.suggest_filter_url(keyword)
            
            # Verificar si existe
            filter_exists = any(
                suggested.lower() in f or f.endswith(suggested.lower())
                for f in existing_filters
            )
            
            if not filter_exists and volume > 50:
                priority = 'HIGH' if volume > 500 else ('MEDIUM' if volume > 200 else 'LOW')
                gaps.append({
                    'keyword': keyword,
                    'volume': volume,
                    'intent': intent,
                    'suggested_filter': suggested,
                    'priority': priority
                })
        
        gaps_df = pd.DataFrame(gaps)
        if not gaps_df.empty:
            gaps_df = gaps_df.sort_values('volume', ascending=False)
        
        self.results.gaps = gaps_df
        return gaps_df
    
    # ═══════════════════════════════════════════════════════════════════════════
    # RECOMENDACIONES
    # ═══════════════════════════════════════════════════════════════════════════
    
    def generate_recommendations(self) -> List[Dict]:
        """Genera recomendaciones priorizadas"""
        recommendations = []
        
        # 1. Orden óptimo de facetas (UX)
        if self.results.facet_priority_order:
            order_str = ' > '.join(self.results.facet_priority_order[:4])
            recommendations.append({
                'priority': 0,
                'type': 'UX_ARCHITECTURE',
                'action': f'Orden óptimo de facetas en UI: {order_str}',
                'reason': 'Basado en comportamiento real de usuarios',
                'impact': 'HIGH'
            })
        
        # 2. Canibalizaciones
        if not self.results.cannibalization.empty:
            for _, row in self.results.cannibalization.head(5).iterrows():
                impact = float(row['impact_score']) if hasattr(row['impact_score'], 'item') else row['impact_score']
                if impact > 10:
                    recommendations.append({
                        'priority': 1,
                        'type': 'CANNIBALIZATION',
                        'action': f"Crear filtro: {row['suggested_filter']}",
                        'reason': f"Artículo canibalizando '{row['top_query']}' ({impact:.0f} clics)",
                        'impact': impact
                    })
        
        # 3. Gaps de demanda
        if not self.results.gaps.empty:
            for _, row in self.results.gaps[self.results.gaps['priority'] == 'HIGH'].head(5).iterrows():
                volume = int(row['volume']) if hasattr(row['volume'], 'item') else row['volume']
                recommendations.append({
                    'priority': 2,
                    'type': 'DEMAND_GAP',
                    'action': f"Crear filtro: {row['suggested_filter']}",
                    'reason': f"Keyword '{row['keyword']}' sin filtro ({volume} búsquedas/mes)",
                    'impact': volume
                })
        
        # 4. Gaps UX vs SEO
        if not self.results.ux_seo_matrix.empty:
            for _, row in self.results.ux_seo_matrix.iterrows():
                if 'Oportunidad de visibilidad' in str(row.get('opportunity', '')):
                    ux_share = float(row['ux_share']) if hasattr(row['ux_share'], 'item') else row['ux_share']
                    seo_share = float(row['seo_share']) if hasattr(row['seo_share'], 'item') else row['seo_share']
                    sessions = int(row['total_sessions']) if hasattr(row['total_sessions'], 'item') else row['total_sessions']
                    recommendations.append({
                        'priority': 3,
                        'type': 'UX_SEO_GAP',
                        'action': f"Mejorar SEO de faceta: {row['facet_type']}",
                        'reason': f"Alta navegación interna ({ux_share:.1f}%) pero baja visibilidad SEO ({seo_share:.1f}%)",
                        'impact': sessions
                    })
        
        # 5. Filtros a NOINDEX
        noindex = self.processor.data.get('noindex_filters', pd.DataFrame())
        if not noindex.empty:
            for facet_type in noindex['facet_type'].unique():
                recommendations.append({
                    'priority': 4,
                    'type': 'INDEXATION',
                    'action': f"NOINDEX filtros de {facet_type}",
                    'reason': 'Ordenación/Precio no deben indexarse',
                    'impact': 'MEDIUM'
                })
        
        recommendations.sort(key=lambda x: x['priority'])
        self.results.recommendations = recommendations
        return recommendations
    
    def generate_summary(self) -> Dict:
        """Genera resumen ejecutivo"""
        summary = {
            'total_urls': 0,
            'filters_count': 0,
            'articles_count': 0,
            'total_clicks': 0,
            'cannibalization_rate': 0.0,
            'cannibalized_clicks': 0,
            'gaps_found': 0,
            'high_priority_gaps': 0,
            'facet_order': self.results.facet_priority_order[:4] if self.results.facet_priority_order else [],
            'top_facet': None,
            'top_facet_pct': 0.0
        }
        
        if not self.results.url_classification.empty:
            df = self.results.url_classification
            summary['total_urls'] = int(len(df))
            summary['filters_count'] = int(len(df[df['url_type'] == 'FILTER']))
            summary['articles_count'] = int(len(df[df['url_type'] == 'ARTICLE']))
            
            clicks_col = 'clicks' if 'clicks' in df.columns else 'url_total_clicks'
            if clicks_col in df.columns:
                summary['total_clicks'] = int(df[clicks_col].sum())
        
        if not self.results.cannibalization.empty:
            summary['cannibalized_clicks'] = int(self.results.cannibalization['impact_score'].sum())
            if summary['total_clicks'] > 0:
                summary['cannibalization_rate'] = round(
                    float(summary['cannibalized_clicks']) / float(summary['total_clicks']) * 100, 2
                )
        
        if not self.results.gaps.empty:
            summary['gaps_found'] = int(len(self.results.gaps))
            summary['high_priority_gaps'] = int(len(self.results.gaps[self.results.gaps['priority'] == 'HIGH']))
        
        if not self.results.facet_usage.empty:
            top = self.results.facet_usage.iloc[0]
            summary['top_facet'] = str(top['facet_type'])
            summary['top_facet_pct'] = float(top['pct_usage'])
        
        self.results.summary = summary
        return summary


class IndexationAnalyzer:
    """Analiza reglas de indexación"""
    
    # Umbrales de indexación (configurables)
    N2_CLICKS_THRESHOLD = 500
    N2_DEMAND_THRESHOLD = 200
    N1_MIN_CLICKS = 50
    
    def __init__(self, processor: DataProcessor):
        self.processor = processor
    
    def should_index(self, url: str, clicks: int = 0, 
                     demand: int = 0, position: float = 100) -> Tuple[bool, str]:
        """Determina si una URL debe indexarse"""
        url_info = self.processor.classify_url(url)
        
        # Nunca indexar: sorting, pagination, price
        if url_info['has_sorting']:
            return False, "Ordenación - canonical sin parámetro"
        if url_info['has_pagination']:
            return False, "Paginación - canonical a página 1"
        if url_info['has_price']:
            return False, "Filtro de precio - usar AJAX"
        
        # Nunca indexar 3+ facetas
        if url_info['num_facets'] >= 3:
            return False, "3+ facetas - canonical al padre N2"
        
        # N2: necesita umbral
        if url_info['num_facets'] == 2:
            if clicks >= self.N2_CLICKS_THRESHOLD or demand >= self.N2_DEMAND_THRESHOLD:
                return True, f"N2 con demanda suficiente (clicks={clicks}, demand={demand})"
            return False, f"N2 bajo umbral (necesita >{self.N2_CLICKS_THRESHOLD} clicks ó >{self.N2_DEMAND_THRESHOLD} demanda)"
        
        # N1: generalmente indexar
        if url_info['num_facets'] == 1:
            return True, "N1 - indexar con contenido"
        
        # Categoría: siempre indexar
        if url_info['type'] == 'CATEGORY':
            return True, "Categoría principal"
        
        # Artículos: siempre indexar
        if url_info['type'] == 'ARTICLE':
            return True, "Artículo/guía"
        
        return True, "Default: indexar"
    
    def audit_urls(self, urls_df: pd.DataFrame) -> pd.DataFrame:
        """Audita todas las URLs para indexación"""
        results = []
        
        clicks_col = 'clicks' if 'clicks' in urls_df.columns else 'url_total_clicks'
        
        for _, row in urls_df.iterrows():
            url = row.get('url', '')
            clicks = row.get(clicks_col, 0)
            
            should_idx, reason = self.should_index(url, clicks)
            
            results.append({
                'url': url,
                'should_index': should_idx,
                'reason': reason,
                'current_clicks': clicks,
                'action': 'INDEX' if should_idx else 'NOINDEX + CANONICAL'
            })
        
        return pd.DataFrame(results)
