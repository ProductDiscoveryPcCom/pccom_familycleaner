"""
Analyzers Module - CORREGIDO
Lógica central de análisis UX + SEO con cruce de datos
"""
import pandas as pd
import numpy as np
import re
from typing import Dict, List, Tuple, Optional, Any
from collections import defaultdict
from .data_processor import DataProcessor, AnalysisResults


class ArchitectureAnalyzer:
    """Analiza la arquitectura de navegación facetada (UX) y su visibilidad SEO"""
    
    # Patrones para detectar tipos de facetas en URLs
    FACET_PATTERNS = {
        'size': [r'\d{2,3}-pulgadas', r'\d{2,3}-polegadas'],
        'technology': ['oled', 'qled', 'mini-led', 'miniled', 'nanocell', 'qned', 'ambilight', 'led', 'lcd', 'micro-led', 'microled'],
        'brand': ['samsung', 'lg', 'sony', 'philips', 'tcl', 'hisense', 'xiaomi', 'nilait', 'toshiba', 'panasonic', 'tcl-corporation'],
        'connectivity': ['smart-tv', 'wifi', 'bluetooth'],
        'condition': ['nuevo', 'reacondicionado', 'seminuevo', 'novo', 'recondicionado'],
        'refresh_rate': [r'\d+-hz'],
        'use_case': ['gaming', 'deportes', 'cine'],
        'color': ['negro', 'blanco', 'gris', 'preto', 'branco'],
        'resolution': ['4k', '8k', 'full-hd', 'uhd', '3840', '7680'],
        'featured': ['recomendados', 'pack', 'ofertas'],
        'rating': [r'\d+-estrellas', 'estrelas']
    }
    
    def __init__(self, category_keyword: str):
        self.category = category_keyword.lower()
        self.url_analysis = []
        self.level_distribution = {}
        self.facet_combinations = {}
        self.architecture_recommendation = {}
    
    def classify_url_segment(self, segment: str) -> Tuple[str, str]:
        """Clasifica un segmento de URL en tipo de faceta"""
        segment = segment.lower().strip()
        
        for facet_type, patterns in self.FACET_PATTERNS.items():
            for pattern in patterns:
                if pattern.startswith(r'\\d') or '\\d' in pattern:
                    # Es regex
                    if re.match(pattern.replace('\\d', r'\d'), segment):
                        return (facet_type, segment)
                else:
                    # Es string literal
                    if pattern in segment or segment == pattern:
                        return (facet_type, segment)
        
        return ('other', segment)
    
    def analyze_url_structure(self, url: str) -> Dict[str, Any]:
        """Analiza la estructura completa de una URL"""
        url_lower = url.lower()
        
        # Extraer path después de la categoría
        pattern = rf'/{self.category}(/[^?]*)?'
        match = re.search(pattern, url_lower)
        if not match:
            return None
        
        path = match.group(1) or ''
        path = path.strip('/')
        
        # Detectar parámetros
        has_price = '?price' in url_lower or 'price_from' in url_lower
        has_order = 'order=' in url_lower
        
        if not path:
            return {
                'level': 0,
                'facets': [],
                'facet_types': [],
                'facet_order': [],
                'has_price': has_price,
                'has_order': has_order,
                'path': f'/{self.category}',
                'is_clean': True
            }
        
        # Separar segmentos y clasificar
        segments = [s for s in path.split('/') if s]
        facets = []
        facet_types = []
        
        for seg in segments:
            facet_type, facet_value = self.classify_url_segment(seg)
            facets.append((facet_type, facet_value))
            facet_types.append(facet_type)
        
        # Detectar si es URL "limpia" (sin múltiples valores del mismo tipo)
        is_clean = len(facet_types) == len(set(facet_types))
        
        return {
            'level': len(facets),
            'facets': facets,
            'facet_types': facet_types,
            'facet_order': list(dict.fromkeys(facet_types)),  # Orden único
            'has_price': has_price,
            'has_order': has_order,
            'path': f'/{self.category}/{path}',
            'is_clean': is_clean
        }
    
    def analyze_urls(self, urls_df: pd.DataFrame) -> Dict[str, Any]:
        """Analiza todas las URLs y extrae patrones de arquitectura"""
        
        if urls_df is None or urls_df.empty:
            return {}
        
        results = []
        
        for _, row in urls_df.iterrows():
            url = row.get('url', '')
            sessions = row.get('sessions', 0)
            
            structure = self.analyze_url_structure(url)
            if structure:
                structure['sessions'] = sessions
                structure['url'] = url
                results.append(structure)
        
        if not results:
            return {}
        
        df = pd.DataFrame(results)
        
        # Distribución por nivel
        level_dist = df.groupby('level').agg({
            'url': 'count',
            'sessions': 'sum'
        }).reset_index()
        level_dist.columns = ['level', 'url_count', 'sessions']
        total_sessions = level_dist['sessions'].sum()
        level_dist['pct'] = (level_dist['sessions'] / total_sessions * 100).round(2)
        
        self.level_distribution = level_dist.to_dict('records')
        
        # Combinaciones de facetas más usadas (solo URLs limpias)
        clean_urls = df[df['is_clean'] & (df['level'] > 0)]
        combo_dist = clean_urls.groupby(clean_urls['facet_types'].apply(tuple)).agg({
            'url': 'count',
            'sessions': 'sum'
        }).reset_index()
        combo_dist.columns = ['combination', 'url_count', 'sessions']
        combo_dist = combo_dist.sort_values('sessions', ascending=False)
        
        self.facet_combinations = combo_dist.head(20).to_dict('records')
        
        # Análisis por nivel
        analysis = {
            'total_urls': len(df),
            'total_sessions': int(total_sessions),
            'level_distribution': self.level_distribution,
            'facet_combinations': self.facet_combinations,
            'n1_analysis': self._analyze_n1(df),
            'n2_analysis': self._analyze_n2(df),
            'n3_plus_analysis': self._analyze_n3_plus(df),
            'price_filter_usage': self._analyze_price_filters(df),
            'recommended_architecture': self._generate_architecture_recommendation(df)
        }
        
        return analysis
    
    def _analyze_n1(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Analiza URLs de primer nivel (una sola faceta)"""
        n1 = df[df['level'] == 1]
        if n1.empty:
            return {}
        
        # Agrupar por tipo de faceta
        n1_by_type = []
        for _, row in n1.iterrows():
            if row['facet_types']:
                n1_by_type.append({
                    'facet_type': row['facet_types'][0],
                    'sessions': row['sessions']
                })
        
        if not n1_by_type:
            return {}
        
        n1_df = pd.DataFrame(n1_by_type)
        n1_grouped = n1_df.groupby('facet_type')['sessions'].sum().reset_index()
        n1_grouped = n1_grouped.sort_values('sessions', ascending=False)
        total = n1_grouped['sessions'].sum()
        n1_grouped['pct'] = (n1_grouped['sessions'] / total * 100).round(2)
        
        return {
            'total_sessions': int(total),
            'total_urls': len(n1),
            'by_facet_type': n1_grouped.to_dict('records'),
            'top_facet': n1_grouped.iloc[0]['facet_type'] if len(n1_grouped) > 0 else None,
            'recommendation': 'INDEX all N1 pages with clean URLs'
        }
    
    def _analyze_n2(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Analiza URLs de segundo nivel (dos facetas)"""
        n2 = df[(df['level'] == 2) & df['is_clean']]
        if n2.empty:
            return {}
        
        # Analizar orden de facetas
        order_counts = defaultdict(int)
        for _, row in n2.iterrows():
            if len(row['facet_types']) == 2:
                order_key = f"{row['facet_types'][0]} → {row['facet_types'][1]}"
                order_counts[order_key] += row['sessions']
        
        sorted_orders = sorted(order_counts.items(), key=lambda x: -x[1])
        
        return {
            'total_sessions': int(n2['sessions'].sum()),
            'total_urls': len(n2),
            'facet_orders': [{'order': k, 'sessions': v} for k, v in sorted_orders[:10]],
            'optimal_order': sorted_orders[0][0] if sorted_orders else None,
            'recommendation': 'INDEX N2 pages with high search volume combinations'
        }
    
    def _analyze_n3_plus(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Analiza URLs de tercer nivel o más"""
        n3_plus = df[df['level'] >= 3]
        if n3_plus.empty:
            return {}
        
        return {
            'total_sessions': int(n3_plus['sessions'].sum()),
            'total_urls': len(n3_plus),
            'pct_of_total': round(n3_plus['sessions'].sum() / df['sessions'].sum() * 100, 2),
            'recommendation': 'NOINDEX N3+ pages, use canonical to N1/N2'
        }
    
    def _analyze_price_filters(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Analiza uso de filtros de precio"""
        with_price = df[df['has_price']]
        without_price = df[~df['has_price']]
        
        return {
            'with_price': {
                'urls': len(with_price),
                'sessions': int(with_price['sessions'].sum())
            },
            'without_price': {
                'urls': len(without_price),
                'sessions': int(without_price['sessions'].sum())
            },
            'recommendation': 'NOINDEX price-filtered URLs, handle via AJAX'
        }
    
    def _generate_architecture_recommendation(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Genera recomendación de arquitectura óptima"""
        
        # Determinar orden óptimo basado en N1
        n1 = df[df['level'] == 1]
        if n1.empty:
            return {}
        
        n1_by_type = []
        for _, row in n1.iterrows():
            if row['facet_types']:
                n1_by_type.append({
                    'facet_type': row['facet_types'][0],
                    'sessions': row['sessions']
                })
        
        if not n1_by_type:
            return {}
        
        n1_df = pd.DataFrame(n1_by_type)
        n1_grouped = n1_df.groupby('facet_type')['sessions'].sum().reset_index()
        n1_grouped = n1_grouped.sort_values('sessions', ascending=False)
        
        # Facetas navegables (excluir 'other', 'featured', etc.)
        navigable_facets = ['size', 'brand', 'technology', 'connectivity', 'resolution', 'refresh_rate', 'use_case']
        optimal_order = [f for f in n1_grouped['facet_type'].tolist() if f in navigable_facets][:5]
        
        # Calcular qué indexar
        total_sessions = df['sessions'].sum()
        n0_sessions = df[df['level'] == 0]['sessions'].sum()
        n1_sessions = df[df['level'] == 1]['sessions'].sum()
        n2_sessions = df[(df['level'] == 2) & df['is_clean']]['sessions'].sum()
        
        # URLs recomendadas para indexar
        indexable_pct = round((n0_sessions + n1_sessions + n2_sessions * 0.5) / total_sessions * 100, 1)
        
        return {
            'optimal_facet_order': optimal_order,
            'url_structure': {
                'N0': {'pattern': f'/{self.category}', 'index': 'YES', 'pct': round(n0_sessions/total_sessions*100, 1)},
                'N1': {'pattern': f'/{self.category}/{{facet}}', 'index': 'YES', 'pct': round(n1_sessions/total_sessions*100, 1)},
                'N2': {'pattern': f'/{self.category}/{{facet1}}/{{facet2}}', 'index': 'SELECTIVE', 'pct': round(n2_sessions/total_sessions*100, 1)},
                'N3+': {'pattern': f'/{self.category}/{{facet1}}/{{facet2}}/{{facet3}}...', 'index': 'NO', 'pct': round((total_sessions - n0_sessions - n1_sessions - n2_sessions)/total_sessions*100, 1)}
            },
            'indexable_percentage': indexable_pct,
            'seo_recommendations': [
                f'Indexar todas las URLs N0 y N1 ({round((n0_sessions + n1_sessions)/total_sessions*100, 1)}% del tráfico)',
                f'Indexar selectivamente N2 con volumen de búsqueda (combinaciones como {optimal_order[0]}+{optimal_order[1] if len(optimal_order) > 1 else "brand"})',
                'NOINDEX para N3+ y URLs con parámetros de precio',
                f'Canonical de N3+ al ancestro N1 o N2 más relevante'
            ]
        }


class InsightGenerator:
    """Genera insights de alto valor combinando múltiples fuentes de datos"""
    
    @staticmethod
    def generate_all_insights(processor, analyzer) -> Dict[str, Any]:
        """
        Genera todos los insights combinando:
        - Search Filters: Uso de facetas (qué filtran los usuarios)
        - Page Full URL: Arquitectura de URLs (niveles N0, N1, N2...)
        - Top Query: Rendimiento SEO
        """
        
        insights = []
        data = {
            'facet_usage': {},
            'size_analysis': [],
            'brand_analysis': [],
            'tech_analysis': [],
            'cannibalization': [],
            'content_mapping': [],
            'architecture': {},
            'architecture_seo': {},
            'metrics': {},
            'insights': [],
            'data_sources': []  # Tracking de qué fuentes se usaron
        }
        
        category = processor.category_keyword if processor else 'categoria'
        
        # ═══════════════════════════════════════════════════════════════════════
        # FUENTE 1: Page Full URL → Arquitectura de URLs (Niveles N0, N1, N2...)
        # ═══════════════════════════════════════════════════════════════════════
        url_all = processor.data.get('filter_usage_url_all')
        url_seo = processor.data.get('filter_usage_url_seo')
        
        has_url_data = url_all is not None and len(url_all) > 0
        
        if has_url_data:
            data['data_sources'].append('Page Full URL (Todo)')
            
            arch_analyzer = ArchitectureAnalyzer(category)
            arch_analysis = arch_analyzer.analyze_urls(url_all)
            data['architecture'] = arch_analysis
            
            # Métricas de arquitectura
            data['metrics']['total_url_sessions'] = arch_analysis.get('total_sessions', 0)
            data['metrics']['total_urls_analyzed'] = arch_analysis.get('total_urls', 0)
            
            # Generar insights de arquitectura
            if arch_analysis.get('recommended_architecture'):
                rec = arch_analysis['recommended_architecture']
                optimal_order = rec.get('optimal_facet_order', [])
                
                if optimal_order:
                    insights.append({
                        'title': f'Arquitectura óptima de URLs detectada',
                        'description': f'Orden de facetas basado en {arch_analysis.get("total_sessions", 0):,} sesiones de navegación: {" > ".join([f.upper() for f in optimal_order[:4]])}',
                        'action': f'Estructurar URLs como /{category}/{{size}}/{{technology}}/{{brand}}',
                        'priority': 'HIGH',
                        'category': 'architecture',
                        'source': 'Page Full URL'
                    })
                
                # Insight sobre distribución por nivel
                url_struct = rec.get('url_structure', {})
                n0_pct = url_struct.get('N0', {}).get('pct', 0)
                n1_pct = url_struct.get('N1', {}).get('pct', 0)
                n2_pct = url_struct.get('N2', {}).get('pct', 0)
                n3_pct = url_struct.get('N3+', {}).get('pct', 0)
                
                if n1_pct > 30:
                    insights.append({
                        'title': f'N1 concentra {n1_pct:.1f}% del tráfico',
                        'description': f'Las URLs de primer nivel (/{category}/{{faceta}}) son las más importantes. N0+N1 = {n0_pct + n1_pct:.1f}%',
                        'action': 'Asegurar que todas las N1 están indexadas y tienen contenido optimizado',
                        'priority': 'HIGH',
                        'category': 'architecture',
                        'source': 'Page Full URL'
                    })
                
                if n3_pct > 10:
                    insights.append({
                        'title': f'URLs N3+ representan {n3_pct:.1f}% del tráfico',
                        'description': 'Alto uso de URLs con 3+ facetas. Muchas combinaciones que deberían tener NOINDEX.',
                        'action': 'Implementar NOINDEX en N3+ y canonical al ancestro N1/N2 más relevante',
                        'priority': 'MEDIUM',
                        'category': 'architecture',
                        'source': 'Page Full URL'
                    })
            
            # Insights de combinaciones N2
            if arch_analysis.get('n2_analysis'):
                n2 = arch_analysis['n2_analysis']
                if n2.get('facet_orders'):
                    top_combos = n2['facet_orders'][:3]
                    combo_str = ', '.join([c['order'] for c in top_combos])
                    insights.append({
                        'title': f'Top combinaciones N2: {combo_str}',
                        'description': f'Candidatas para indexación selectiva basado en uso real.',
                        'action': f'Verificar que existen filtros indexados para estas combinaciones',
                        'priority': 'MEDIUM',
                        'category': 'architecture',
                        'source': 'Page Full URL'
                    })
            
            # Análisis SEO de arquitectura
            if url_seo is not None and len(url_seo) > 0:
                data['data_sources'].append('Page Full URL (SEO)')
                
                arch_seo = ArchitectureAnalyzer(category)
                seo_analysis = arch_seo.analyze_urls(url_seo)
                data['architecture_seo'] = seo_analysis
                
                data['metrics']['total_seo_url_sessions'] = seo_analysis.get('total_sessions', 0)
                
                # Comparar distribución UX vs SEO por nivel
                if arch_analysis.get('level_distribution') and seo_analysis.get('level_distribution'):
                    ux_levels = {l['level']: l['pct'] for l in arch_analysis['level_distribution']}
                    seo_levels = {l['level']: l['pct'] for l in seo_analysis['level_distribution']}
                    
                    for level in [0, 1, 2]:
                        ux_pct = ux_levels.get(level, 0)
                        seo_pct = seo_levels.get(level, 0)
                        gap = seo_pct - ux_pct
                        
                        if abs(gap) > 5:
                            direction = 'más tráfico SEO' if gap > 0 else 'más navegación interna'
                            insights.append({
                                'title': f'Gap en N{level}: {abs(gap):.1f}% {direction}',
                                'description': f'Navegación interna: {ux_pct:.1f}% vs Tráfico SEO: {seo_pct:.1f}%',
                                'action': 'El SEO capta bien este nivel' if gap > 0 else 'Oportunidad SEO: optimizar TITLEs y contenido',
                                'priority': 'MEDIUM' if abs(gap) > 10 else 'LOW',
                                'category': 'architecture',
                                'source': 'Page Full URL'
                            })
        
        # ═══════════════════════════════════════════════════════════════════════
        # FUENTE 2: Search Filters → Uso de Facetas (qué filtran los usuarios)
        # ═══════════════════════════════════════════════════════════════════════
        filter_all = processor.data.get('filter_usage_all')
        filter_seo = processor.data.get('filter_usage_seo')
        
        has_filter_data = filter_all is not None and len(filter_all) > 0
        
        if has_filter_data:
            data['data_sources'].append('Search Filters (Todo)')
            
            # Agrupar por tipo de faceta
            facet_grouped = filter_all.groupby('facet_type')['sessions'].sum().reset_index()
            total_sessions = facet_grouped['sessions'].sum()
            
            seo_grouped = None
            total_seo = 0
            if filter_seo is not None and len(filter_seo) > 0:
                data['data_sources'].append('Search Filters (SEO)')
                seo_grouped = filter_seo.groupby('facet_type')['sessions'].sum()
                total_seo = seo_grouped.sum()
            
            for _, row in facet_grouped.iterrows():
                facet_type = row['facet_type']
                sessions_all = row['sessions']
                sessions_seo = seo_grouped.get(facet_type, 0) if seo_grouped is not None else 0
                
                pct_all = (sessions_all / total_sessions * 100) if total_sessions > 0 else 0
                pct_seo = (sessions_seo / total_seo * 100) if total_seo > 0 else 0
                seo_ratio = (sessions_seo / sessions_all * 100) if sessions_all > 0 else 0
                
                data['facet_usage'][facet_type] = {
                    'sessions_all': int(sessions_all),
                    'sessions_seo': int(sessions_seo),
                    'pct_all': round(pct_all, 2),
                    'pct_seo': round(pct_seo, 2),
                    'seo_ratio': round(seo_ratio, 2)
                }
            
            # Métricas de Search Filters
            data['metrics']['total_internal_sessions'] = int(total_sessions)
            data['metrics']['total_seo_sessions'] = int(total_seo)
            data['metrics']['seo_ratio'] = round((total_seo / total_sessions * 100) if total_sessions > 0 else 0, 2)
            
            # Insight: Orden óptimo de facetas desde Search Filters
            navegables = {k: v for k, v in data['facet_usage'].items() 
                         if k not in ['sorting', 'price', 'total', 'featured', 'condition', 'other', 'search filters']}
            if navegables:
                orden = sorted(navegables.items(), key=lambda x: -x[1]['pct_all'])
                insights.append({
                    'title': f'Prioridad de facetas por uso',
                    'description': f'Basado en {total_sessions:,} interacciones con filtros: {" > ".join([f[0].upper() for f in orden[:4]])}',
                    'action': f'Ordenar facetas en el UI según este ranking de uso',
                    'priority': 'HIGH',
                    'category': 'facets',
                    'source': 'Search Filters'
                })
            
            # Análisis por Tamaño
            size_all = filter_all[filter_all['facet_type'] == 'size'].groupby('facet_value')['sessions'].sum()
            size_seo = pd.Series(dtype=float)
            if filter_seo is not None:
                size_seo = filter_seo[filter_seo['facet_type'] == 'size'].groupby('facet_value')['sessions'].sum()
            
            for size_val in size_all.index:
                try:
                    size_num = int(size_val)
                    sessions_all = size_all.get(size_val, 0)
                    sessions_seo = size_seo.get(size_val, 0)
                    
                    data['size_analysis'].append({
                        'size': size_val,
                        'size_num': size_num,
                        'sessions_all': int(sessions_all),
                        'sessions_seo': int(sessions_seo),
                        'seo_ratio': round((sessions_seo / sessions_all * 100) if sessions_all > 0 else 0, 2)
                    })
                except:
                    continue
            
            data['size_analysis'].sort(key=lambda x: -x['sessions_all'])
            
            if data['size_analysis']:
                top_sizes = [s['size'] for s in data['size_analysis'][:3]]
                top_pct = sum(s["sessions_all"] for s in data["size_analysis"][:3]) / sum(s["sessions_all"] for s in data["size_analysis"]) * 100 if data['size_analysis'] else 0
                insights.append({
                    'title': f'Tamaños más demandados: {", ".join(top_sizes)}',
                    'description': f'Estos 3 tamaños representan el {top_pct:.0f}% del uso de filtros de tamaño',
                    'action': 'Asegurar que estos filtros tienen contenido optimizado y están indexados',
                    'priority': 'MEDIUM',
                    'category': 'size',
                    'source': 'Search Filters'
                })
            
            # Análisis por Marca
            brand_all = filter_all[filter_all['facet_type'] == 'brand'].groupby('facet_value')['sessions'].sum()
            brand_seo = pd.Series(dtype=float)
            if filter_seo is not None:
                brand_seo = filter_seo[filter_seo['facet_type'] == 'brand'].groupby('facet_value')['sessions'].sum()
            
            total_brand_all = brand_all.sum()
            total_brand_seo = brand_seo.sum()
            
            for brand_val in brand_all.index:
                sessions_all = brand_all.get(brand_val, 0)
                sessions_seo = brand_seo.get(brand_val, 0)
                
                internal_share = (sessions_all / total_brand_all * 100) if total_brand_all > 0 else 0
                seo_share = (sessions_seo / total_brand_seo * 100) if total_brand_seo > 0 else 0
                
                data['brand_analysis'].append({
                    'brand': brand_val,
                    'internal_sessions': int(sessions_all),
                    'seo_sessions': int(sessions_seo),
                    'internal_share': round(internal_share, 2),
                    'seo_share': round(seo_share, 2),
                    'gap': round(internal_share - seo_share, 2)
                })
            
            data['brand_analysis'].sort(key=lambda x: -x['internal_sessions'])
            
            if data['brand_analysis']:
                leader = data['brand_analysis'][0]
                insights.append({
                    'title': f'{leader["brand"].title()} lidera con {leader["internal_share"]:.1f}% del share',
                    'description': f'Seguido por {data["brand_analysis"][1]["brand"].title() if len(data["brand_analysis"]) > 1 else "N/A"}',
                    'priority': 'LOW',
                    'category': 'brand',
                    'source': 'Search Filters'
                })
                
                # Marcas con oportunidad SEO (más UX que SEO)
                high_ux_brands = [b for b in data['brand_analysis'] if b['gap'] > 3]
                if high_ux_brands:
                    brands_str = ', '.join([b['brand'].title() for b in high_ux_brands[:3]])
                    insights.append({
                        'title': f'Oportunidad SEO en marcas: {brands_str}',
                        'description': 'Estas marcas tienen más uso interno que tráfico SEO. Los usuarios las buscan internamente pero no llegan desde Google.',
                        'action': 'Optimizar TITLEs de filtros de marca y crear contenido "mejor [marca] 2025"',
                        'priority': 'MEDIUM',
                        'category': 'brand',
                        'source': 'Search Filters'
                    })
            
            # Análisis por Tecnología
            tech_all = filter_all[filter_all['facet_type'] == 'technology'].groupby('facet_value')['sessions'].sum()
            tech_seo = pd.Series(dtype=float)
            if filter_seo is not None:
                tech_seo = filter_seo[filter_seo['facet_type'] == 'technology'].groupby('facet_value')['sessions'].sum()
            
            for tech_val in tech_all.index:
                sessions_all = tech_all.get(tech_val, 0)
                sessions_seo = tech_seo.get(tech_val, 0)
                
                data['tech_analysis'].append({
                    'technology': tech_val,
                    'sessions_all': int(sessions_all),
                    'sessions_seo': int(sessions_seo)
                })
            
            data['tech_analysis'].sort(key=lambda x: -x['sessions_all'])
        
        # ═══════════════════════════════════════════════════════════════════════
        # FUENTE 3: Top Query → Rendimiento SEO y Canibalización
        # ═══════════════════════════════════════════════════════════════════════
        top_query = processor.data.get('top_query')
        
        if top_query is not None and len(top_query) > 0:
            data['data_sources'].append('Top Query (GSC)')
            
            cannibalization_cases = analyzer.detect_cannibalization() if analyzer else []
            
            for case in cannibalization_cases[:20]:
                data['cannibalization'].append({
                    'query': case.get('query', ''),
                    'ranking_url': case.get('ranking_url', ''),
                    'target_url': case.get('suggested_url', ''),
                    'clicks': case.get('clicks', 0),
                    'priority': case.get('priority', 'LOW')
                })
            
            high_priority = [c for c in data['cannibalization'] if c['priority'] == 'HIGH']
            if high_priority:
                total_clicks = sum(c['clicks'] for c in high_priority)
                insights.append({
                    'title': f'{len(high_priority)} casos de canibalización críticos',
                    'description': f'{total_clicks} clics/mes en queries transaccionales yendo a artículos informativos',
                    'action': 'Crear/verificar filtros correspondientes y ajustar TITLEs de artículos',
                    'priority': 'HIGH',
                    'category': 'cannibalization',
                    'source': 'Top Query'
                })
            
            clicks_col = 'clicks' if 'clicks' in top_query.columns else 'url_total_clicks'
            articles = top_query[top_query['url'].str.contains('mejor|guia|como|comparativa', case=False, na=False)]
            filters = top_query[~top_query['url'].str.contains('mejor|guia|como|comparativa', case=False, na=False)]
            
            data['metrics']['articles_count'] = len(articles)
            data['metrics']['filters_count'] = len(filters)
            data['metrics']['total_gsc_clicks'] = int(top_query[clicks_col].sum()) if clicks_col in top_query.columns else 0
            data['metrics']['total_urls'] = len(top_query)
        
        # ═══════════════════════════════════════════════════════════════════════
        # COMBINAR INSIGHTS: Cruzar datos de múltiples fuentes
        # ═══════════════════════════════════════════════════════════════════════
        
        # Si tenemos AMBAS fuentes (Search Filters + Page URL), generar insights cruzados
        if has_filter_data and has_url_data:
            # Comparar orden de facetas de ambas fuentes
            sf_order = sorted(
                [(k, v['pct_all']) for k, v in data['facet_usage'].items() 
                 if k not in ['sorting', 'price', 'total', 'other', 'search filters']],
                key=lambda x: -x[1]
            )
            
            url_order = data['architecture'].get('recommended_architecture', {}).get('optimal_facet_order', [])
            
            if sf_order and url_order:
                sf_top = [f[0] for f in sf_order[:3]]
                url_top = url_order[:3]
                
                # Verificar si coinciden
                if sf_top == url_top:
                    insights.append({
                        'title': '✅ Consistencia confirmada entre fuentes',
                        'description': f'Tanto Search Filters como Page URL coinciden en el orden: {" > ".join([f.upper() for f in sf_top])}',
                        'action': 'El orden de facetas está validado por ambas fuentes de datos',
                        'priority': 'LOW',
                        'category': 'cross-validation',
                        'source': 'Search Filters + Page Full URL'
                    })
                else:
                    insights.append({
                        'title': '⚠️ Diferencia entre fuentes de datos',
                        'description': f'Search Filters sugiere: {" > ".join([f.upper() for f in sf_top])} | URLs sugiere: {" > ".join([f.upper() for f in url_top])}',
                        'action': 'Investigar la diferencia - puede indicar patrones distintos de navegación vs URL structure',
                        'priority': 'MEDIUM',
                        'category': 'cross-validation',
                        'source': 'Search Filters + Page Full URL'
                    })
        
        # Gap UX vs SEO desde Search Filters
        if data['facet_usage']:
            for facet_type, facet_data in data['facet_usage'].items():
                if facet_type in ['total', 'other', 'sorting', 'price', 'search filters']:
                    continue
                    
                gap = facet_data['pct_all'] - facet_data['pct_seo']
                if abs(gap) > 5:
                    direction = 'más uso interno que SEO' if gap > 0 else 'más SEO que uso interno'
                    insights.append({
                        'title': f'Gap en {facet_type.upper()}: {gap:+.1f}%',
                        'description': f'Esta faceta tiene {direction}. Gap mayor al 5% indica desalineación.',
                        'action': f'{"Optimizar SEO de filtros" if gap > 0 else "Mejorar navegación interna"} de {facet_type}',
                        'priority': 'MEDIUM',
                        'category': 'gap',
                        'source': 'Search Filters'
                    })
        
        # Ordenar insights por prioridad
        priority_order = {'HIGH': 0, 'MEDIUM': 1, 'LOW': 2}
        insights.sort(key=lambda x: priority_order.get(x.get('priority', 'LOW'), 2))
        
        data['insights'] = insights
        
        return data


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
