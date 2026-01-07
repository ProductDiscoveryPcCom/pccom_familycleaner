"""
Analyzers Module - CORREGIDO v2
Lógica central de análisis UX + SEO con cruce de datos
Incluye generación de Sistema de Navegación (Capa 1) y Reglas de Indexación (Capa 2)
"""
import pandas as pd
import numpy as np
import re
from typing import Dict, List, Tuple, Optional, Any
from collections import defaultdict
from .data_processor import DataProcessor, AnalysisResults


class ArchitectureAnalyzer:
    """Analiza la arquitectura de navegación facetada (UX) y su visibilidad SEO"""
    
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
                    if re.match(pattern.replace('\\d', r'\d'), segment):
                        return (facet_type, segment)
                else:
                    if pattern in segment or segment == pattern:
                        return (facet_type, segment)
        
        return ('other', segment)
    
    def analyze_url_structure(self, url: str) -> Dict[str, Any]:
        """Analiza la estructura completa de una URL"""
        url_lower = url.lower()
        
        pattern = rf'/{self.category}(/[^?]*)?'
        match = re.search(pattern, url_lower)
        if not match:
            return None
        
        path = match.group(1) or ''
        path = path.strip('/')
        
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
        
        segments = [s for s in path.split('/') if s]
        facets = []
        facet_types = []
        
        for seg in segments:
            facet_type, facet_value = self.classify_url_segment(seg)
            facets.append((facet_type, facet_value))
            facet_types.append(facet_type)
        
        is_clean = len(facet_types) == len(set(facet_types))
        
        return {
            'level': len(facets),
            'facets': facets,
            'facet_types': facet_types,
            'facet_order': list(dict.fromkeys(facet_types)),
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
        
        level_dist = df.groupby('level').agg({
            'url': 'count',
            'sessions': 'sum'
        }).reset_index()
        level_dist.columns = ['level', 'url_count', 'sessions']
        total_sessions = level_dist['sessions'].sum()
        level_dist['pct'] = (level_dist['sessions'] / total_sessions * 100).round(2)
        
        self.level_distribution = level_dist.to_dict('records')
        
        clean_urls = df[df['is_clean'] & (df['level'] > 0)]
        combo_dist = clean_urls.groupby(clean_urls['facet_types'].apply(tuple)).agg({
            'url': 'count',
            'sessions': 'sum'
        }).reset_index()
        combo_dist.columns = ['combination', 'url_count', 'sessions']
        combo_dist = combo_dist.sort_values('sessions', ascending=False)
        
        self.facet_combinations = combo_dist.head(20).to_dict('records')
        
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
        """Analiza URLs de primer nivel"""
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
        """Analiza URLs de segundo nivel"""
        n2 = df[(df['level'] == 2) & df['is_clean']]
        if n2.empty:
            return {}
        
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
        
        navigable_facets = ['size', 'brand', 'technology', 'connectivity', 'resolution', 'refresh_rate', 'use_case']
        optimal_order = [f for f in n1_grouped['facet_type'].tolist() if f in navigable_facets][:5]
        
        total_sessions = df['sessions'].sum()
        n0_sessions = df[df['level'] == 0]['sessions'].sum()
        n1_sessions = df[df['level'] == 1]['sessions'].sum()
        n2_sessions = df[(df['level'] == 2) & df['is_clean']]['sessions'].sum()
        
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


class NavigationSystemGenerator:
    """
    Genera el análisis de Sistema de Navegación en dos capas:
    - Capa 1: Sistema de Navegación (UX) - Basado en datos de uso interno
    - Capa 2: Reglas de Indexación (SEO) - Qué URLs indexar y cuáles no
    """
    
    def __init__(self, category: str, processor: 'DataProcessor', analyzer: 'FacetAnalyzer'):
        self.category = category
        self.processor = processor
        self.analyzer = analyzer
    
    def generate_layer1_ux(self) -> Dict[str, Any]:
        """
        Genera Capa 1: Sistema de Navegación (UX)
        Basado en datos de uso interno: cómo navegan realmente los usuarios
        """
        layer1 = {
            'title': 'Sistema de Navegación (UX)',
            'subtitle': 'Basado en datos de uso interno: cómo navegan realmente los usuarios',
            'facets': []
        }
        
        filter_all = self.processor.data.get('filter_usage_all', pd.DataFrame())
        
        if filter_all.empty:
            return layer1
        
        total_sessions = filter_all['sessions'].sum()
        
        facet_grouped = filter_all.groupby('facet_type')['sessions'].sum().reset_index()
        facet_grouped['pct'] = (facet_grouped['sessions'] / total_sessions * 100).round(1)
        facet_grouped = facet_grouped.sort_values('sessions', ascending=False)
        
        facet_config = {
            'size': {
                'name': 'Tamaño',
                'icon': '📐',
                'color': '#00d9ff',
                'description': 'Primer filtro visible. El más usado.',
                'generates_url': True,
                'url_pattern': f'/{self.category}/{{size}}-pulgadas',
                'content_suggestion': 'Intro + medidas + distancia + FAQ'
            },
            'brand': {
                'name': 'Marca',
                'icon': '🏷️',
                'color': '#ffd93d',
                'description': 'Segundo filtro más usado.',
                'generates_url': True,
                'url_pattern': f'/{self.category}/{{marca}}',
                'content_suggestion': 'Info marca + gamas + para quién'
            },
            'price': {
                'name': 'Precio',
                'icon': '💰',
                'color': '#00ff88',
                'description': 'Siempre visible, NO genera URL.',
                'generates_url': False,
                'url_pattern': None,
                'content_suggestion': 'Rangos infinitos = no indexable',
                'noindex_reason': 'No genera URL (AJAX)'
            },
            'technology': {
                'name': 'Tecnología',
                'icon': '⚡',
                'color': '#ff6b6b',
                'description': 'Bajo uso pero alta intención de compra.',
                'generates_url': True,
                'url_pattern': f'/{self.category}/{{tecnologia}}',
                'content_suggestion': 'Explicación tecnología + comparativa'
            },
            'use_case': {
                'name': 'Por Uso',
                'icon': '🎯',
                'color': '#a855f7',
                'description': 'Landings para usuarios que no saben qué buscar.',
                'generates_url': True,
                'url_pattern': f'/{self.category}/{{uso}}',
                'content_suggestion': 'Selección curada, no filtro automático',
                'is_curated': True
            },
            'feature': {
                'name': 'Características',
                'icon': '⚙️',
                'color': '#888888',
                'description': 'Colapsado por defecto. Refinamiento.',
                'generates_url': True,
                'url_pattern': f'/{self.category}/{{feature}}',
                'content_suggestion': 'Solo 120Hz y HDMI 2.1 (gaming) indexables',
                'selective_index': True
            },
            'refresh_rate': {
                'name': 'Frecuencia',
                'icon': '🔄',
                'color': '#3b82f6',
                'description': 'Para gamers. 120Hz y 144Hz.',
                'generates_url': True,
                'url_pattern': f'/{self.category}/{{hz}}-hz',
                'content_suggestion': 'Gaming + compatibilidad consolas'
            },
            'condition': {
                'name': 'Estado',
                'icon': '♻️',
                'color': '#10b981',
                'description': 'Reacondicionados con demanda creciente.',
                'generates_url': True,
                'url_pattern': f'/{self.category}/reacondicionado',
                'content_suggestion': 'Garantías + proceso + ahorro'
            },
            'connectivity': {
                'name': 'Conectividad',
                'icon': '📡',
                'color': '#6366f1',
                'description': 'Smart TV es expectativa base.',
                'generates_url': True,
                'url_pattern': f'/{self.category}/smart-tv',
                'content_suggestion': 'Sistemas operativos + apps'
            }
        }
        
        for _, row in facet_grouped.iterrows():
            facet_type = row['facet_type']
            if facet_type in ['total', 'sorting', 'other', 'search filters']:
                continue
            
            config = facet_config.get(facet_type, {
                'name': facet_type.replace('_', ' ').title(),
                'icon': '📦',
                'color': '#888888',
                'description': '',
                'generates_url': True,
                'url_pattern': f'/{self.category}/{{value}}',
                'content_suggestion': ''
            })
            
            facet_values = filter_all[filter_all['facet_type'] == facet_type].nlargest(8, 'sessions')
            top_values = facet_values['facet_value'].tolist()
            highlighted_values = top_values[:3]
            
            facet_data = {
                'type': facet_type,
                'name': config['name'],
                'icon': config['icon'],
                'color': config['color'],
                'usage_pct': row['pct'],
                'total_sessions': int(row['sessions']),
                'description': config['description'],
                'generates_url': config['generates_url'],
                'url_pattern': config.get('url_pattern'),
                'content_suggestion': config.get('content_suggestion', ''),
                'top_values': top_values,
                'highlighted_values': highlighted_values,
                'is_curated': config.get('is_curated', False),
                'selective_index': config.get('selective_index', False),
                'noindex_reason': config.get('noindex_reason')
            }
            
            layer1['facets'].append(facet_data)
        
        layer1['facets'].sort(key=lambda x: -x['usage_pct'])
        
        return layer1
    
    def generate_layer2_seo(self) -> Dict[str, Any]:
        """
        Genera Capa 2: Reglas de Indexación (SEO)
        Qué URLs indexar y con qué condiciones
        """
        layer2 = {
            'title': 'Reglas de Indexación (SEO)',
            'subtitle': 'Qué URLs indexar y con qué condiciones',
            'url_rule': f'/{self.category}/{{atributo1}}/{{atributo2}} — Orden fijo: tamaño > tecnología > marca',
            'index_rules': [],
            'noindex_rules': {}
        }
        
        index_rules = [
            {
                'pattern': f'/{self.category}',
                'index': True,
                'min_content': '500+ palabras + FAQ',
                'condition': 'Siempre',
                'example': f'/{self.category}'
            },
            {
                'pattern': f'/{self.category}/{{tamaño}}',
                'index': True,
                'min_content': '150 palabras + FAQ',
                'condition': 'Todos los tamaños estándar',
                'example': f'/{self.category}/55-pulgadas'
            },
            {
                'pattern': f'/{self.category}/{{marca}}',
                'index': True,
                'min_content': '200 palabras',
                'condition': 'Marcas con >50 clics demanda',
                'example': f'/{self.category}/samsung'
            },
            {
                'pattern': f'/{self.category}/{{tecnología}}',
                'index': True,
                'min_content': '150 palabras',
                'condition': 'Tecnologías diferenciadas (no /led, no /4k)',
                'example': f'/{self.category}/oled'
            },
            {
                'pattern': f'/{self.category}/{{uso}}',
                'index': True,
                'min_content': '300 palabras',
                'condition': 'Landings curadas con demanda',
                'example': f'/{self.category}/gaming'
            },
            {
                'pattern': f'/{{tamaño}}/{{tecnología}}',
                'index': True,
                'min_content': '80 palabras',
                'condition': 'Si demanda KW >200 Ó clics GSC >500',
                'example': f'/{self.category}/55-pulgadas/oled'
            },
            {
                'pattern': f'/{{tamaño}}/{{marca}}',
                'index': True,
                'min_content': '80 palabras',
                'condition': 'Si demanda KW >100 Ó clics GSC >500',
                'example': f'/{self.category}/65-pulgadas/samsung'
            }
        ]
        
        noindex_rules = {
            '3+_attributes': {
                'title': '3+ ATRIBUTOS',
                'description': 'URLs con 3 o más facetas',
                'examples': [
                    '/55/oled/lg',
                    '/65/samsung/qled',
                    '/32/smart-tv/lg',
                    'etc.'
                ],
                'action': 'canonical → padre N2'
            },
            'parameters': {
                'title': 'PARÁMETROS',
                'description': 'URLs con query strings',
                'examples': [
                    '?order=price_asc',
                    '?order=price_desc',
                    '?order=rating',
                    '?page=2,3,4...',
                    '?price_from=X'
                ],
                'action': 'canonical → sin parámetro'
            },
            'redundant': {
                'title': 'REDUNDANTES',
                'description': 'Atributos que no diferencian',
                'examples': [
                    '/4k (95% productos)',
                    '/hdr (redundante)',
                    '/led (genérico)',
                    '/blanco /negro',
                    '/wifi /bluetooth',
                    '/crystal-uhd'
                ],
                'action': 'No indexar (redundantes)'
            }
        }
        
        layer2['index_rules'] = index_rules
        layer2['noindex_rules'] = noindex_rules
        
        return layer2
    
    def generate_full_system(self) -> Dict[str, Any]:
        """Genera el sistema completo de navegación con ambas capas"""
        return {
            'category': self.category,
            'layer1_ux': self.generate_layer1_ux(),
            'layer2_seo': self.generate_layer2_seo(),
            'generated_at': pd.Timestamp.now().isoformat()
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
            'data_sources': [],
            'navigation_system': {}
        }
        
        category = processor.category_keyword if processor else 'categoria'
        
        # ═══════════════════════════════════════════════════════════════════════
        # FUENTE 1: Page Full URL → Arquitectura de URLs
        # ═══════════════════════════════════════════════════════════════════════
        url_all = processor.data.get('filter_usage_url_all')
        url_seo = processor.data.get('filter_usage_url_seo')
        
        has_url_data = url_all is not None and len(url_all) > 0
        
        if has_url_data:
            data['data_sources'].append('Page Full URL (Todo)')
            
            arch_analyzer = ArchitectureAnalyzer(category)
            arch_analysis = arch_analyzer.analyze_urls(url_all)
            data['architecture'] = arch_analysis
            
            data['metrics']['total_url_sessions'] = arch_analysis.get('total_sessions', 0)
            data['metrics']['total_urls_analyzed'] = arch_analysis.get('total_urls', 0)
            
            if arch_analysis.get('recommended_architecture'):
                rec = arch_analysis['recommended_architecture']
                optimal_order = rec.get('optimal_facet_order', [])
                
                if optimal_order:
                    insights.append({
                        'title': f'Arquitectura óptima de URLs detectada',
                        'description': f'Orden de facetas basado en {arch_analysis.get("total_sessions", 0):,} sesiones: {" > ".join([f.upper() for f in optimal_order[:4]])}',
                        'action': f'Estructurar URLs como /{category}/{{size}}/{{technology}}/{{brand}}',
                        'priority': 'HIGH',
                        'category': 'architecture',
                        'source': 'Page Full URL'
                    })
                
                url_struct = rec.get('url_structure', {})
                n0_pct = url_struct.get('N0', {}).get('pct', 0)
                n1_pct = url_struct.get('N1', {}).get('pct', 0)
                n3_pct = url_struct.get('N3+', {}).get('pct', 0)
                
                if n1_pct > 30:
                    insights.append({
                        'title': f'N1 concentra {n1_pct:.1f}% del tráfico',
                        'description': f'URLs de primer nivel son las más importantes. N0+N1 = {n0_pct + n1_pct:.1f}%',
                        'action': 'Asegurar que todas las N1 están indexadas con contenido optimizado',
                        'priority': 'HIGH',
                        'category': 'architecture',
                        'source': 'Page Full URL'
                    })
                
                if n3_pct > 10:
                    insights.append({
                        'title': f'URLs N3+ representan {n3_pct:.1f}% del tráfico',
                        'description': 'Alto uso de URLs con 3+ facetas que deberían tener NOINDEX.',
                        'action': 'Implementar NOINDEX en N3+ y canonical al ancestro N1/N2',
                        'priority': 'MEDIUM',
                        'category': 'architecture',
                        'source': 'Page Full URL'
                    })
            
            if arch_analysis.get('n2_analysis'):
                n2 = arch_analysis['n2_analysis']
                if n2.get('facet_orders'):
                    top_combos = n2['facet_orders'][:3]
                    combo_str = ', '.join([c['order'] for c in top_combos])
                    insights.append({
                        'title': f'Top combinaciones N2: {combo_str}',
                        'description': f'Candidatas para indexación selectiva.',
                        'action': f'Verificar filtros indexados para estas combinaciones',
                        'priority': 'MEDIUM',
                        'category': 'architecture',
                        'source': 'Page Full URL'
                    })
            
            if url_seo is not None and len(url_seo) > 0:
                data['data_sources'].append('Page Full URL (SEO)')
                arch_seo = ArchitectureAnalyzer(category)
                seo_analysis = arch_seo.analyze_urls(url_seo)
                data['architecture_seo'] = seo_analysis
                data['metrics']['total_seo_url_sessions'] = seo_analysis.get('total_sessions', 0)
        
        # ═══════════════════════════════════════════════════════════════════════
        # FUENTE 2: Search Filters → Uso de Facetas
        # ═══════════════════════════════════════════════════════════════════════
        filter_all = processor.data.get('filter_usage_all')
        filter_seo = processor.data.get('filter_usage_seo')
        
        has_filter_data = filter_all is not None and len(filter_all) > 0
        
        if has_filter_data:
            data['data_sources'].append('Search Filters (Todo)')
            
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
            
            data['metrics']['total_internal_sessions'] = int(total_sessions)
            data['metrics']['total_seo_sessions'] = int(total_seo)
            data['metrics']['seo_ratio'] = round((total_seo / total_sessions * 100) if total_sessions > 0 else 0, 2)
            
            navegables = {k: v for k, v in data['facet_usage'].items() 
                         if k not in ['sorting', 'price', 'total', 'featured', 'condition', 'other', 'search filters']}
            if navegables:
                orden = sorted(navegables.items(), key=lambda x: -x[1]['pct_all'])
                insights.append({
                    'title': f'Prioridad de facetas por uso',
                    'description': f'Basado en {total_sessions:,} interacciones: {" > ".join([f[0].upper() for f in orden[:4]])}',
                    'action': f'Ordenar facetas en el UI según este ranking',
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
                    'description': f'Estos 3 tamaños representan el {top_pct:.0f}% del uso',
                    'action': 'Asegurar filtros con contenido optimizado e indexados',
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
                
                high_ux_brands = [b for b in data['brand_analysis'] if b['gap'] > 3]
                if high_ux_brands:
                    brands_str = ', '.join([b['brand'].title() for b in high_ux_brands[:3]])
                    insights.append({
                        'title': f'Oportunidad SEO en marcas: {brands_str}',
                        'description': 'Más uso interno que tráfico SEO.',
                        'action': 'Optimizar TITLEs de filtros de marca',
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
            
            # *** FIX: detect_cannibalization devuelve DataFrame, no lista ***
            cannibalization_df = pd.DataFrame()
            if analyzer:
                try:
                    cannibalization_df = analyzer.detect_cannibalization()
                except Exception as e:
                    cannibalization_df = pd.DataFrame()
            
            # Iterar sobre DataFrame correctamente
            if cannibalization_df is not None and not cannibalization_df.empty:
                for _, case in cannibalization_df.head(20).iterrows():
                    data['cannibalization'].append({
                        'query': str(case.get('top_query', '')),
                        'ranking_url': str(case.get('url', '')),
                        'target_url': str(case.get('suggested_filter', '')),
                        'clicks': int(case.get('impact_score', 0)) if pd.notna(case.get('impact_score')) else 0,
                        'priority': 'HIGH' if case.get('impact_score', 0) > 50 else ('MEDIUM' if case.get('impact_score', 0) > 10 else 'LOW')
                    })
            
            high_priority = [c for c in data['cannibalization'] if c['priority'] == 'HIGH']
            if high_priority:
                total_clicks = sum(c['clicks'] for c in high_priority)
                insights.append({
                    'title': f'{len(high_priority)} casos de canibalización críticos',
                    'description': f'{total_clicks} clics/mes en queries transaccionales',
                    'action': 'Crear/verificar filtros y ajustar TITLEs de artículos',
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
        # GENERAR SISTEMA DE NAVEGACIÓN (CAPAS 1 y 2)
        # ═══════════════════════════════════════════════════════════════════════
        if has_filter_data:
            nav_generator = NavigationSystemGenerator(category, processor, analyzer)
            data['navigation_system'] = nav_generator.generate_full_system()
        
        # ═══════════════════════════════════════════════════════════════════════
        # CRUZAR INSIGHTS
        # ═══════════════════════════════════════════════════════════════════════
        if has_filter_data and has_url_data:
            sf_order = sorted(
                [(k, v['pct_all']) for k, v in data['facet_usage'].items() 
                 if k not in ['sorting', 'price', 'total', 'other', 'search filters']],
                key=lambda x: -x[1]
            )
            
            url_order = data['architecture'].get('recommended_architecture', {}).get('optimal_facet_order', [])
            
            if sf_order and url_order:
                sf_top = [f[0] for f in sf_order[:3]]
                url_top = url_order[:3]
                
                if sf_top == url_top:
                    insights.append({
                        'title': '✅ Consistencia confirmada entre fuentes',
                        'description': f'Ambas fuentes coinciden: {" > ".join([f.upper() for f in sf_top])}',
                        'action': 'El orden de facetas está validado',
                        'priority': 'LOW',
                        'category': 'cross-validation',
                        'source': 'Search Filters + Page Full URL'
                    })
                else:
                    insights.append({
                        'title': '⚠️ Diferencia entre fuentes',
                        'description': f'Search Filters: {" > ".join([f.upper() for f in sf_top])} | URLs: {" > ".join([f.upper() for f in url_top])}',
                        'action': 'Investigar diferencia en patrones',
                        'priority': 'MEDIUM',
                        'category': 'cross-validation',
                        'source': 'Search Filters + Page Full URL'
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
    
    def analyze_filter_usage(self, source: str = 'all') -> pd.DataFrame:
        df_key = f'filter_usage_{source}'
        if df_key not in self.processor.data:
            return pd.DataFrame()
        
        df = self.processor.data[df_key].copy()
        df = df[~df['facet_type'].isin(['total', 'sorting', 'other'])]
        
        total_sessions = df['sessions'].sum()
        
        facet_summary = df.groupby('facet_type').agg({
            'sessions': 'sum',
            'facet_value': 'count'
        }).reset_index()
        
        facet_summary.columns = ['facet_type', 'total_sessions', 'num_values']
        facet_summary['pct_usage'] = (facet_summary['total_sessions'] / total_sessions * 100).round(2)
        facet_summary = facet_summary.sort_values('total_sessions', ascending=False)
        
        self.results.facet_priority_order = facet_summary['facet_type'].tolist()
        self.results.facet_usage = facet_summary
        
        return facet_summary
    
    def get_top_values_per_facet(self, source: str = 'all', top_n: int = 10) -> Dict[str, pd.DataFrame]:
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
    
    def analyze_url_distribution(self, top_query_df: pd.DataFrame = None) -> pd.DataFrame:
        if top_query_df is None:
            top_query_df = self.processor.data.get('top_query', pd.DataFrame())
        
        if top_query_df.empty:
            return pd.DataFrame()
        
        df = top_query_df.copy()
        
        url_info = df['url'].apply(self.processor.classify_url)
        df['url_type'] = url_info.apply(lambda x: x['type'])
        df['num_facets'] = url_info.apply(lambda x: x['num_facets'])
        df['has_sorting'] = url_info.apply(lambda x: x['has_sorting'])
        df['has_pagination'] = url_info.apply(lambda x: x['has_pagination'])
        df['has_price'] = url_info.apply(lambda x: x['has_price'])
        
        facets = url_info.apply(lambda x: x['facets'])
        df['facet_size'] = facets.apply(lambda x: x.get('size'))
        df['facet_brand'] = facets.apply(lambda x: x.get('brand'))
        df['facet_technology'] = facets.apply(lambda x: x.get('technology'))
        df['facet_connectivity'] = facets.apply(lambda x: x.get('connectivity'))
        
        df['query_intent'] = df['top_query'].apply(self.processor.classify_query_intent)
        
        self.results.url_classification = df
        return df
    
    def detect_cannibalization(self, top_query_df: pd.DataFrame = None) -> pd.DataFrame:
        """Detecta canibalización - DEVUELVE DataFrame"""
        df = self.analyze_url_distribution(top_query_df)
        
        if df.empty:
            self.results.cannibalization = pd.DataFrame()
            return pd.DataFrame()
        
        cannib = df[
            (df['url_type'] == 'ARTICLE') & 
            (df['query_intent'] == 'TRANSACTIONAL')
        ].copy()
        
        if cannib.empty:
            self.results.cannibalization = pd.DataFrame()
            return pd.DataFrame()
        
        cannib['suggested_filter'] = cannib['top_query'].apply(
            self.processor.suggest_filter_url
        )
        
        clicks_col = 'top_query_clicks' if 'top_query_clicks' in cannib.columns else 'clicks'
        if clicks_col not in cannib.columns:
            clicks_col = 'url_total_clicks'
        
        cannib['impact_score'] = cannib[clicks_col].fillna(0) if clicks_col in cannib.columns else 0
        cannib = cannib.sort_values('impact_score', ascending=False)
        
        self.results.cannibalization = cannib
        return cannib
    
    def analyze_facet_performance(self, top_query_df: pd.DataFrame = None) -> pd.DataFrame:
        df = self.analyze_url_distribution(top_query_df)
        
        if df.empty:
            return pd.DataFrame()
        
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
    
    def analyze_ux_seo_matrix(self) -> pd.DataFrame:
        usage_df = self.results.facet_usage
        perf_df = self.results.facet_performance
        
        if usage_df.empty or perf_df.empty:
            return pd.DataFrame()
        
        seo_by_type = perf_df.groupby('facet_type').agg({
            'total_clicks': 'sum',
            'avg_position': 'mean',
            'num_urls': 'sum'
        }).reset_index()
        seo_by_type.columns = ['facet_type', 'seo_clicks', 'seo_avg_position', 'seo_urls']
        
        matrix = usage_df.merge(seo_by_type, on='facet_type', how='outer')
        matrix = matrix.fillna(0)
        
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
        
        matrix['ux_seo_gap'] = matrix['ux_share'] - matrix['seo_share']
        
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
        df_key = f'filter_usage_{usage_source}'
        if df_key not in self.processor.data:
            return pd.DataFrame()
        
        usage = self.processor.data[df_key].copy()
        usage = usage[~usage['facet_type'].isin(['total', 'sorting', 'other', 'price'])]
        
        perf = self.results.facet_performance
        if perf.empty:
            return pd.DataFrame()
        
        usage['join_key'] = usage['facet_type'] + '_' + usage['facet_value'].astype(str).str.lower()
        perf['join_key'] = perf['facet_type'] + '_' + perf['facet_value'].astype(str).str.lower()
        
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
        
        matrix['seo_ux_ratio'] = np.where(
            matrix['ux_sessions'] > 0,
            matrix['seo_clicks'] / matrix['ux_sessions'],
            0
        )
        
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
    
    def detect_gaps(self, keyword_df: pd.DataFrame = None, 
                   top_query_df: pd.DataFrame = None) -> pd.DataFrame:
        if keyword_df is None:
            keyword_df = self.processor.data.get('keyword_research', pd.DataFrame())
        
        if keyword_df.empty:
            return pd.DataFrame()
        
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
    
    def generate_recommendations(self) -> List[Dict]:
        recommendations = []
        
        if self.results.facet_priority_order:
            order_str = ' > '.join(self.results.facet_priority_order[:4])
            recommendations.append({
                'priority': 0,
                'type': 'UX_ARCHITECTURE',
                'action': f'Orden óptimo de facetas en UI: {order_str}',
                'reason': 'Basado en comportamiento real de usuarios',
                'impact': 'HIGH'
            })
        
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
    
    N2_CLICKS_THRESHOLD = 500
    N2_DEMAND_THRESHOLD = 200
    N1_MIN_CLICKS = 50
    
    def __init__(self, processor: DataProcessor):
        self.processor = processor
    
    def should_index(self, url: str, clicks: int = 0, 
                     demand: int = 0, position: float = 100) -> Tuple[bool, str]:
        url_info = self.processor.classify_url(url)
        
        if url_info['has_sorting']:
            return False, "Ordenación - canonical sin parámetro"
        if url_info['has_pagination']:
            return False, "Paginación - canonical a página 1"
        if url_info['has_price']:
            return False, "Filtro de precio - usar AJAX"
        
        if url_info['num_facets'] >= 3:
            return False, "3+ facetas - canonical al padre N2"
        
        if url_info['num_facets'] == 2:
            if clicks >= self.N2_CLICKS_THRESHOLD or demand >= self.N2_DEMAND_THRESHOLD:
                return True, f"N2 con demanda suficiente (clicks={clicks}, demand={demand})"
            return False, f"N2 bajo umbral (necesita >{self.N2_CLICKS_THRESHOLD} clicks ó >{self.N2_DEMAND_THRESHOLD} demanda)"
        
        if url_info['num_facets'] == 1:
            return True, "N1 - indexar con contenido"
        
        if url_info['type'] == 'CATEGORY':
            return True, "Categoría principal"
        
        if url_info['type'] == 'ARTICLE':
            return True, "Artículo/guía"
        
        return True, "Default: indexar"
    
    def audit_urls(self, urls_df: pd.DataFrame) -> pd.DataFrame:
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
