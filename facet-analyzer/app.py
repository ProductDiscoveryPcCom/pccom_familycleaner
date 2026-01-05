"""
Facet Architecture Analyzer - CORREGIDO
Herramienta de análisis UX + SEO para navegación facetada
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
from io import BytesIO, StringIO
from datetime import datetime

from utils import DataProcessor, FacetAnalyzer, IndexationAnalyzer, LLMValidator, AnalysisResults, InsightGenerator, ReportGenerator

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURACIÓN
# ═══════════════════════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="Facet Architecture Analyzer",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS personalizado
st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        background: linear-gradient(90deg, #00d9ff, #00ff88);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin-bottom: 0.5rem;
    }
    .metric-card {
        background: linear-gradient(135deg, rgba(0,217,255,0.1), rgba(0,255,136,0.1));
        border-radius: 10px;
        padding: 1rem;
        border: 1px solid rgba(0,217,255,0.2);
    }
    .success-box {
        background: rgba(0, 255, 136, 0.1);
        border: 1px solid rgba(0, 255, 136, 0.3);
        border-radius: 10px;
        padding: 1rem;
        margin: 0.5rem 0;
    }
    .warning-box {
        background: rgba(255, 217, 61, 0.1);
        border: 1px solid rgba(255, 217, 61, 0.3);
        border-radius: 10px;
        padding: 1rem;
        margin: 0.5rem 0;
    }
    .error-box {
        background: rgba(255, 107, 107, 0.1);
        border: 1px solid rgba(255, 107, 107, 0.3);
        border-radius: 10px;
        padding: 1rem;
        margin: 0.5rem 0;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        padding: 10px 20px;
    }
</style>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# SESSION STATE
# ═══════════════════════════════════════════════════════════════════════════════

def init_session_state():
    defaults = {
        'processor': None,
        'analyzer': None,
        'data_loaded': False,
        'analysis_complete': False,
        'llm_validator': None,
        'category': 'televisores',
        'insights_data': None,
        'reports_generated': False
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


# ═══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ═══════════════════════════════════════════════════════════════════════════════

def render_sidebar():
    with st.sidebar:
        st.markdown("## ⚙️ Configuración")
        
        category = st.text_input(
            "Categoría a analizar",
            value=st.session_state.get('category', 'televisores'),
            help="Keyword de la categoría (ej: televisores, portatiles, moviles)"
        )
        st.session_state.category = category
        
        st.markdown("---")
        st.markdown("## 📁 Cargar Datos")
        
        # Archivos con explicación de formato
        with st.expander("ℹ️ Formatos esperados"):
            st.markdown("""
            **Top Query (BigQuery):** CSV con columnas `url`, `url_total_clicks`, `top_query`...
            
            **GSC Consultas/Páginas:** Export directo de Search Console (español)
            
            **Keyword Research:** Export de Google Keyword Planner (UTF-16)
            
            **Uso Filtros:** Export de Adobe Analytics con formato `faceta:valor,sesiones`
            """)
        
        top_query_file = st.file_uploader("📊 Top Query por URL", type=['csv'], key='tq')
        gsc_queries_file = st.file_uploader("🔍 GSC Consultas", type=['csv'], key='gscq')
        gsc_pages_file = st.file_uploader("📄 GSC Páginas", type=['csv'], key='gscp')
        keyword_file = st.file_uploader("🔑 Keyword Research", type=['csv', 'tsv'], key='kw')
        
        st.markdown("**📈 Uso de Filtros (Adobe Analytics)**")
        
        filter_format = st.radio(
            "Formato de datos",
            ["Search Filters", "Page Full URL"],
            help="Search Filters: faceta:valor | Page Full URL: URLs completas"
        )
        
        filter_all_file = st.file_uploader("Todo tráfico", type=['csv'], key='fall')
        filter_seo_file = st.file_uploader("Solo SEO", type=['csv'], key='fseo')
        
        st.markdown("---")
        
        # API Keys
        with st.expander("🔑 API Keys (Validación IA)"):
            anthropic_key = st.text_input("Anthropic API Key", type="password", key='ant_key')
            openai_key = st.text_input("OpenAI API Key", type="password", key='oai_key')
            
            if anthropic_key or openai_key:
                st.session_state.llm_validator = LLMValidator(
                    anthropic_key=anthropic_key or None,
                    openai_key=openai_key or None
                )
                st.success("✅ API Keys configuradas")
        
        st.markdown("---")
        
        if st.button("🚀 Procesar Datos", type="primary", use_container_width=True):
            process_files(
                category=category,
                top_query_file=top_query_file,
                gsc_queries_file=gsc_queries_file,
                gsc_pages_file=gsc_pages_file,
                keyword_file=keyword_file,
                filter_all_file=filter_all_file,
                filter_seo_file=filter_seo_file,
                filter_format=filter_format
            )
        
        return category


def process_files(category, filter_format="Search Filters", **files):
    """Procesa todos los archivos subidos"""
    with st.spinner("Procesando datos..."):
        processor = DataProcessor(category_keyword=category)
        errors = []
        loaded = []
        
        # Top Query
        if files.get('top_query_file'):
            try:
                df = pd.read_csv(files['top_query_file'])
                processor.load_top_query(df)
                loaded.append("Top Query")
            except Exception as e:
                errors.append(f"Top Query: {e}")
        
        # GSC Consultas
        if files.get('gsc_queries_file'):
            try:
                df = pd.read_csv(files['gsc_queries_file'])
                processor.load_gsc_queries(df)
                loaded.append("GSC Consultas")
            except Exception as e:
                errors.append(f"GSC Consultas: {e}")
        
        # GSC Páginas
        if files.get('gsc_pages_file'):
            try:
                df = pd.read_csv(files['gsc_pages_file'])
                processor.load_gsc_pages(df)
                loaded.append("GSC Páginas")
            except Exception as e:
                errors.append(f"GSC Páginas: {e}")
        
        # Keyword Research (encoding especial)
        if files.get('keyword_file'):
            try:
                content = files['keyword_file'].read()
                processor.load_keyword_research(content)
                loaded.append("Keyword Research")
            except Exception as e:
                errors.append(f"Keyword Research: {e}")
        
        # Uso de Filtros - Todo tráfico
        if files.get('filter_all_file'):
            try:
                content = files['filter_all_file'].read().decode('utf-8', errors='ignore')
                if filter_format == "Page Full URL":
                    processor.load_filter_usage_url(content, 'all')
                else:
                    processor.load_filter_usage(content, 'all')
                loaded.append(f"Uso Filtros Todo ({filter_format})")
            except Exception as e:
                errors.append(f"Uso Filtros (Todo): {e}")
        
        # Uso de Filtros - SEO
        if files.get('filter_seo_file'):
            try:
                content = files['filter_seo_file'].read().decode('utf-8', errors='ignore')
                if filter_format == "Page Full URL":
                    processor.load_filter_usage_url(content, 'seo')
                else:
                    processor.load_filter_usage(content, 'seo')
                loaded.append(f"Uso Filtros SEO ({filter_format})")
            except Exception as e:
                errors.append(f"Uso Filtros (SEO): {e}")
        
        if loaded:
            st.session_state.processor = processor
            st.session_state.analyzer = FacetAnalyzer(processor)
            st.session_state.data_loaded = True
            st.success(f"✅ Cargados: {', '.join(loaded)}")
        
        if errors:
            for error in errors:
                st.error(f"❌ {error}")


# ═══════════════════════════════════════════════════════════════════════════════
# TABS DE ANÁLISIS
# ═══════════════════════════════════════════════════════════════════════════════

def run_analysis():
    """Ejecuta todos los análisis"""
    if not st.session_state.data_loaded:
        return False
    
    analyzer = st.session_state.analyzer
    processor = st.session_state.processor
    
    with st.spinner("Ejecutando análisis completo..."):
        # 1. Uso de filtros (UX)
        if 'filter_usage_all' in processor.data:
            analyzer.analyze_filter_usage('all')
        elif 'filter_usage_seo' in processor.data:
            analyzer.analyze_filter_usage('seo')
        
        # 2. Clasificación de URLs (SEO)
        if 'top_query' in processor.data:
            analyzer.analyze_url_distribution(processor.data['top_query'])
            analyzer.detect_cannibalization()
            analyzer.analyze_facet_performance()
        
        # 3. Cruce UX + SEO
        analyzer.analyze_ux_seo_matrix()
        
        # 4. Gaps de demanda
        kw_df = processor.data.get('keyword_research')
        tq_df = processor.data.get('top_query')
        if kw_df is not None:
            analyzer.detect_gaps(kw_df, tq_df)
        
        # 5. Generar recomendaciones
        analyzer.generate_recommendations()
        analyzer.generate_summary()
        
        st.session_state.analysis_complete = True
    
    return True


def render_overview_tab():
    """Tab de resumen ejecutivo"""
    st.markdown("### 📊 Resumen Ejecutivo")
    
    if not st.session_state.data_loaded:
        st.info("👈 Carga los datos desde la barra lateral")
        return
    
    if not st.session_state.analysis_complete:
        if st.button("▶️ Ejecutar Análisis"):
            run_analysis()
            st.rerun()
        return
    
    analyzer = st.session_state.analyzer
    summary = analyzer.results.summary
    
    # Métricas principales
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("URLs Analizadas", f"{summary.get('total_urls', 0):,}")
    with col2:
        st.metric("Filtros", f"{summary.get('filters_count', 0):,}")
    with col3:
        st.metric("Artículos", f"{summary.get('articles_count', 0):,}")
    with col4:
        rate = summary.get('cannibalization_rate', 0)
        st.metric("Canibalización", f"{rate:.1f}%", 
                 delta="OK" if rate < 5 else "Alto", delta_color="inverse" if rate >= 5 else "normal")
    
    st.markdown("---")
    
    # Orden óptimo de facetas
    if summary.get('facet_order'):
        st.markdown("### 🎯 Orden Óptimo de Facetas (UX)")
        order_html = " → ".join([f"**{f.title()}**" for f in summary['facet_order']])
        st.markdown(f"Basado en comportamiento de usuarios: {order_html}")
        
        if summary.get('top_facet'):
            st.markdown(f"*{summary['top_facet'].title()}* representa el **{summary['top_facet_pct']:.1f}%** del uso de filtros")
    
    st.markdown("---")
    
    # Distribución de tráfico
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 📈 Distribución por Tipo de URL")
        url_df = analyzer.results.url_classification
        if not url_df.empty:
            clicks_col = 'clicks' if 'clicks' in url_df.columns else 'url_total_clicks'
            dist = url_df.groupby('url_type')[clicks_col].sum().reset_index()
            dist.columns = ['Tipo', 'Clics']
            
            fig = px.pie(dist, values='Clics', names='Tipo', 
                        color_discrete_sequence=['#00d9ff', '#00ff88', '#ffd93d', '#ff6b6b'])
            fig.update_layout(height=300, margin=dict(t=20, b=20, l=20, r=20))
            st.plotly_chart(fig, width="stretch")
    
    with col2:
        st.markdown("### 🔄 Uso de Facetas (UX)")
        usage_df = analyzer.results.facet_usage
        if not usage_df.empty:
            fig = px.bar(usage_df.head(6), x='facet_type', y='pct_usage',
                        color='pct_usage', color_continuous_scale='Viridis',
                        labels={'facet_type': 'Faceta', 'pct_usage': '% Uso'})
            fig.update_layout(height=300, margin=dict(t=20, b=20, l=20, r=20), showlegend=False)
            st.plotly_chart(fig, width="stretch")
    
    # Estado de canibalización
    st.markdown("---")
    cannib_df = analyzer.results.cannibalization
    
    if not cannib_df.empty and len(cannib_df) > 0:
        total = cannib_df['impact_score'].sum()
        if total < 100:
            st.markdown(f"""
            <div class="success-box">
                <h4>✅ Canibalización Mínima</h4>
                <p>Solo <strong>{int(total)}</strong> clics ({summary.get('cannibalization_rate', 0):.1f}%) canibalizados</p>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="warning-box">
                <h4>⚠️ Canibalización Detectada</h4>
                <p><strong>{int(total)}</strong> clics ({summary.get('cannibalization_rate', 0):.1f}%) canibalizados por artículos</p>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="success-box">
            <h4>✅ Sin Canibalización</h4>
            <p>No se detectó canibalización significativa</p>
        </div>
        """, unsafe_allow_html=True)


def render_ux_seo_tab():
    """Tab de cruce UX + SEO (el más valioso)"""
    st.markdown("### 🔄 Matriz UX + SEO")
    st.markdown("*Cruce entre comportamiento de navegación (UX) y visibilidad en buscadores (SEO)*")
    
    if not st.session_state.analysis_complete:
        st.info("Ejecuta el análisis primero en la pestaña Overview")
        return
    
    analyzer = st.session_state.analyzer
    matrix = analyzer.results.ux_seo_matrix
    
    if matrix.empty:
        st.warning("No hay datos suficientes para el cruce UX + SEO")
        st.info("Necesitas cargar tanto 'Uso de Filtros' como 'Top Query'")
        return
    
    # Gráfico de burbujas
    st.markdown("#### Mapa de Oportunidades")
    
    fig = px.scatter(
        matrix[matrix['total_sessions'] > 0],
        x='ux_share',
        y='seo_share',
        size='total_sessions',
        color='ux_seo_gap',
        hover_name='facet_type',
        color_continuous_scale='RdYlGn',
        labels={
            'ux_share': '% Navegación Interna (UX)',
            'seo_share': '% Tráfico SEO',
            'ux_seo_gap': 'Gap UX-SEO'
        }
    )
    
    # Añadir línea diagonal (equilibrio perfecto)
    fig.add_shape(type="line", x0=0, y0=0, x1=50, y1=50,
                  line=dict(color="gray", dash="dash", width=1))
    
    fig.update_layout(height=400)
    st.plotly_chart(fig, width="stretch")
    
    st.markdown("""
    **Interpretación:**
    - 🟢 Puntos cerca de la diagonal = Equilibrio UX-SEO
    - 🔴 Puntos arriba de la diagonal = Alta SEO, Baja UX (revisar navegación)
    - 🔵 Puntos debajo de la diagonal = Alta UX, Baja SEO (oportunidad de visibilidad)
    """)
    
    st.markdown("---")
    
    # Tabla con oportunidades
    st.markdown("#### Análisis por Tipo de Faceta")
    
    display_df = matrix[['facet_type', 'total_sessions', 'ux_share', 'seo_clicks', 
                         'seo_share', 'ux_seo_gap', 'opportunity']].copy()
    display_df.columns = ['Faceta', 'Sesiones UX', '% UX', 'Clics SEO', '% SEO', 'Gap', 'Oportunidad']
    
    st.dataframe(
        display_df,
        width="stretch",
        hide_index=True
    )
    
    # Detalle granular
    st.markdown("---")
    with st.expander("🔍 Ver detalle por valor de faceta"):
        detail = analyzer.analyze_ux_seo_by_value()
        if not detail.empty:
            st.dataframe(
                detail[['facet_type', 'facet_value', 'ux_sessions', 'seo_clicks', 'status']]
                .head(30),
                width="stretch",
                hide_index=True
            )


def render_cannibalization_tab():
    """Tab de canibalización"""
    st.markdown("### 🔴 Análisis de Canibalización")
    
    if not st.session_state.analysis_complete:
        st.info("Ejecuta el análisis primero")
        return
    
    analyzer = st.session_state.analyzer
    cannib = analyzer.results.cannibalization
    
    if cannib.empty:
        st.success("✅ No se detectó canibalización")
        return
    
    # Métricas
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Casos", len(cannib))
    with col2:
        st.metric("Clics Afectados", f"{cannib['impact_score'].sum():.0f}")
    with col3:
        high = len(cannib[cannib['impact_score'] > 10])
        st.metric("Alto Impacto", high)
    
    st.markdown("---")
    
    # Tabla
    display = cannib[['top_query', 'impact_score', 'url', 'suggested_filter']].copy()
    display.columns = ['Query Transaccional', 'Clics', 'Artículo Rankeando', 'Filtro Sugerido']
    display['Artículo Rankeando'] = display['Artículo Rankeando'].str.replace(
        'https://www.pccomponentes.com/', '/', regex=False
    )
    
    st.dataframe(display.head(20), width="stretch", hide_index=True)
    
    # Validación IA con doble pasada
    if st.session_state.llm_validator:
        st.markdown("---")
        st.markdown("#### 🤖 Validación con IA (Doble Pasada Crítica)")
        st.markdown("""
        <div style="background: rgba(0,217,255,0.1); padding: 1rem; border-radius: 10px; margin-bottom: 1rem;">
        <strong>Metodología:</strong><br>
        1️⃣ <strong>Análisis inicial</strong> → IA analiza los datos<br>
        2️⃣ <strong>Crítica</strong> → Segunda IA (o segunda pasada) critica el análisis<br>
        3️⃣ <strong>Refinamiento</strong> → Se aplican correcciones al resultado final
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("🔄 Ejecutar Doble Validación", type="secondary"):
            with st.spinner("Pasada 1: Análisis inicial..."):
                data = cannib.head(10).to_dict('records')
                result = st.session_state.llm_validator.dual_validate(
                    {"cases": data}, "cannibalization"
                )
                st.session_state.validation_result = result
            
        if 'validation_result' in st.session_state:
            result = st.session_state.validation_result
            
            # Mostrar las 3 pasadas
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.markdown("##### 1️⃣ Análisis Inicial")
                if result.get('pass_1_analysis'):
                    with st.expander("Ver análisis", expanded=False):
                        st.json(result['pass_1_analysis'])
                else:
                    st.warning("No disponible")
            
            with col2:
                st.markdown("##### 2️⃣ Crítica")
                if result.get('pass_2_critique'):
                    critique = result['pass_2_critique']
                    score = critique.get('validation_score', 0)
                    issues = critique.get('major_issues_count', 0)
                    rec = critique.get('recommendation', 'N/A')
                    
                    st.metric("Score", f"{score}/100")
                    st.metric("Issues", issues)
                    st.markdown(f"**Recomendación:** {rec}")
                    
                    with st.expander("Ver crítica completa"):
                        st.json(critique)
                else:
                    st.warning("No disponible")
            
            with col3:
                st.markdown("##### 3️⃣ Resultado Refinado")
                if result.get('final_refined'):
                    refined = result['final_refined']
                    
                    confidence = result.get('confidence', 'LOW')
                    color = {'HIGH': '🟢', 'MEDIUM': '🟡', 'LOW': '🔴'}.get(confidence, '⚪')
                    st.markdown(f"**Confianza:** {color} {confidence}")
                    
                    if refined.get('_corrections'):
                        st.warning(f"⚠️ {len(refined['_corrections'])} correcciones aplicadas")
                    
                    if refined.get('_omissions_to_review'):
                        st.info(f"📝 {len(refined['_omissions_to_review'])} omisiones detectadas")
                    
                    with st.expander("Ver resultado final"):
                        st.json(refined)
                else:
                    st.warning("No disponible")


def render_gaps_tab():
    """Tab de gaps de demanda"""
    st.markdown("### 🎯 Gaps de Demanda")
    
    if not st.session_state.analysis_complete:
        st.info("Ejecuta el análisis primero")
        return
    
    analyzer = st.session_state.analyzer
    gaps = analyzer.results.gaps
    
    if gaps.empty:
        st.info("No se detectaron gaps (o no se cargó Keyword Research)")
        return
    
    # Métricas
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Gaps Totales", len(gaps))
    with col2:
        high = len(gaps[gaps['priority'] == 'HIGH'])
        st.metric("Alta Prioridad", high)
    
    # Filtro
    priority = st.multiselect("Prioridad", ['HIGH', 'MEDIUM', 'LOW'], default=['HIGH', 'MEDIUM'])
    filtered = gaps[gaps['priority'].isin(priority)]
    
    # Gráfico
    fig = px.bar(filtered.head(15), x='keyword', y='volume', color='priority',
                color_discrete_map={'HIGH': '#ff6b6b', 'MEDIUM': '#ffd93d', 'LOW': '#4ecdc4'})
    fig.update_layout(xaxis_tickangle=-45, height=400)
    st.plotly_chart(fig, width="stretch")
    
    # Tabla
    st.dataframe(
        filtered[['keyword', 'volume', 'suggested_filter', 'priority']],
        width="stretch",
        hide_index=True
    )


def render_recommendations_tab():
    """Tab de recomendaciones"""
    st.markdown("### 🚀 Recomendaciones Priorizadas")
    
    if not st.session_state.analysis_complete:
        st.info("Ejecuta el análisis primero")
        return
    
    analyzer = st.session_state.analyzer
    recs = analyzer.results.recommendations
    
    if not recs:
        st.info("No hay recomendaciones")
        return
    
    # Agrupar por prioridad
    priority_labels = {
        0: ("🏆 Arquitectura", "#00d9ff"),
        1: ("🔴 Canibalización", "#ff6b6b"),
        2: ("🟡 Gaps Demanda", "#ffd93d"),
        3: ("🔵 UX/SEO Gap", "#4ecdc4"),
        4: ("⚪ Indexación", "#888")
    }
    
    for priority in sorted(set(r['priority'] for r in recs)):
        label, color = priority_labels.get(priority, (f"Prioridad {priority}", "#888"))
        priority_recs = [r for r in recs if r['priority'] == priority]
        
        st.markdown(f"#### {label}")
        
        for rec in priority_recs[:5]:
            with st.expander(f"{rec['type']}: {rec['action'][:60]}..."):
                st.markdown(f"**Acción:** {rec['action']}")
                st.markdown(f"**Razón:** {rec['reason']}")
                st.markdown(f"**Impacto:** {rec['impact']}")
        
        st.markdown("---")


def render_export_tab():
    """Tab de exportación"""
    st.markdown("### 📥 Exportar Resultados")
    
    if not st.session_state.analysis_complete:
        st.info("Ejecuta el análisis primero")
        return
    
    analyzer = st.session_state.analyzer
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### CSV")
        
        # Canibalización
        if not analyzer.results.cannibalization.empty:
            csv = analyzer.results.cannibalization.to_csv(index=False)
            st.download_button(
                "📥 Descargar Canibalización",
                csv,
                "cannibalization.csv",
                "text/csv"
            )
        
        # Gaps
        if not analyzer.results.gaps.empty:
            csv = analyzer.results.gaps.to_csv(index=False)
            st.download_button(
                "📥 Descargar Gaps",
                csv,
                "gaps.csv",
                "text/csv"
            )
        
        # Matrix UX-SEO
        if not analyzer.results.ux_seo_matrix.empty:
            csv = analyzer.results.ux_seo_matrix.to_csv(index=False)
            st.download_button(
                "📥 Descargar Matrix UX-SEO",
                csv,
                "ux_seo_matrix.csv",
                "text/csv"
            )
    
    with col2:
        st.markdown("#### JSON")
        
        # Recomendaciones
        if analyzer.results.recommendations:
            json_str = json.dumps(analyzer.results.recommendations, indent=2, ensure_ascii=False)
            st.download_button(
                "📥 Descargar Recomendaciones",
                json_str,
                "recommendations.json",
                "application/json"
            )
        
        # Resumen completo
        if analyzer.results.summary:
            json_str = json.dumps(analyzer.results.summary, indent=2, ensure_ascii=False)
            st.download_button(
                "📥 Descargar Resumen",
                json_str,
                "summary.json",
                "application/json"
            )


def render_insights_tab():
    """Tab de Insights de Alto Valor y Reportes HTML"""
    st.markdown("### 💡 Insights Clave & Reportes HTML")
    st.markdown("*Hallazgos de alto valor y dashboards visuales descargables*")
    
    if not st.session_state.data_loaded:
        st.info("Carga los datos primero en la barra lateral")
        return
    
    processor = st.session_state.processor
    analyzer = st.session_state.analyzer
    category = st.session_state.category
    
    # Generar insights si no existen
    if st.session_state.insights_data is None:
        with st.spinner("Generando insights..."):
            st.session_state.insights_data = InsightGenerator.generate_all_insights(processor, analyzer)
    
    insights_data = st.session_state.insights_data
    insights = insights_data.get('insights', [])
    metrics = insights_data.get('metrics', {})
    
    # Métricas principales
    st.markdown("---")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total = metrics.get('total_internal_sessions', 0)
        st.metric("📊 Sesiones Internas", f"{total:,}" if total < 1000000 else f"{total/1000000:.1f}M")
    with col2:
        seo = metrics.get('total_seo_sessions', 0)
        st.metric("🔍 Sesiones SEO", f"{seo:,}" if seo < 1000000 else f"{seo/1000000:.1f}M")
    with col3:
        ratio = metrics.get('seo_ratio', 0)
        st.metric("📈 Ratio SEO", f"{ratio:.1f}%")
    with col4:
        st.metric("💡 Insights Detectados", len(insights))
    
    st.markdown("---")
    
    # Mostrar insights clave
    st.markdown("### 🎯 Hallazgos Clave")
    
    if insights:
        # Separar por prioridad
        high_priority = [i for i in insights if i.get('priority') == 'HIGH']
        medium_priority = [i for i in insights if i.get('priority') == 'MEDIUM']
        low_priority = [i for i in insights if i.get('priority') == 'LOW']
        
        if high_priority:
            st.markdown("#### 🔴 Prioridad Alta")
            for insight in high_priority:
                with st.expander(f"⚠️ {insight.get('title', '')}", expanded=True):
                    st.markdown(f"**Descripción:** {insight.get('description', '')}")
                    if insight.get('action'):
                        st.markdown(f"**Acción recomendada:** {insight.get('action', '')}")
        
        if medium_priority:
            st.markdown("#### 🟡 Prioridad Media")
            for insight in medium_priority:
                with st.expander(f"📌 {insight.get('title', '')}"):
                    st.markdown(f"**Descripción:** {insight.get('description', '')}")
                    if insight.get('action'):
                        st.markdown(f"**Acción recomendada:** {insight.get('action', '')}")
        
        if low_priority:
            st.markdown("#### 🟢 Información")
            for insight in low_priority[:3]:  # Solo mostrar los 3 primeros
                with st.expander(f"ℹ️ {insight.get('title', '')}"):
                    st.markdown(f"**Descripción:** {insight.get('description', '')}")
    else:
        st.info("Carga más datos (especialmente filtros de Adobe Analytics) para generar insights automáticos")
    
    # Visualizaciones rápidas
    st.markdown("---")
    st.markdown("### 📊 Visualizaciones Rápidas")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Gráfico de facetas
        facet_usage = insights_data.get('facet_usage', {})
        if facet_usage:
            facet_df = pd.DataFrame([
                {'Faceta': k.replace('_', ' ').title(), 'Uso (%)': v.get('pct_all', 0)}
                for k, v in facet_usage.items()
                if k not in ['total', 'other', 'sorting', 'price'] and v.get('pct_all', 0) > 0.5
            ]).sort_values('Uso (%)', ascending=False).head(6)
            
            if not facet_df.empty:
                fig = px.pie(facet_df, values='Uso (%)', names='Faceta',
                            title='Distribución de Uso por Faceta',
                            color_discrete_sequence=px.colors.qualitative.Set2)
                fig.update_layout(height=350)
                st.plotly_chart(fig, width="stretch")
    
    with col2:
        # Gráfico de marcas
        brand_data = insights_data.get('brand_analysis', [])
        if brand_data:
            brand_df = pd.DataFrame(brand_data[:6])
            if not brand_df.empty and 'brand' in brand_df.columns:
                fig = px.bar(brand_df, x='brand', y=['internal_share', 'seo_share'],
                            title='Share por Marca: UX vs SEO',
                            labels={'value': 'Share (%)', 'brand': 'Marca', 'variable': 'Tipo'},
                            barmode='group',
                            color_discrete_map={'internal_share': '#00d9ff', 'seo_share': '#00ff88'})
                fig.update_layout(height=350)
                st.plotly_chart(fig, width="stretch")
    
    # Reportes HTML descargables
    st.markdown("---")
    st.markdown("### 📥 Reportes HTML Descargables")
    st.markdown("*Dashboards visuales completos para presentaciones*")
    
    col1, col2, col3, col4 = st.columns(4)
    
    report_gen = ReportGenerator(category, insights_data)
    
    with col1:
        html_arch = report_gen.generate_architecture_report()
        st.download_button(
            "🏗️ Arquitectura de Facetas",
            html_arch,
            f"arquitectura-facetas-{category}.html",
            "text/html",
            use_container_width=True
        )
    
    with col2:
        html_market = report_gen.generate_market_share_report()
        st.download_button(
            "🏆 Market Share",
            html_market,
            f"market-share-{category}.html",
            "text/html",
            use_container_width=True
        )
    
    with col3:
        html_content = report_gen.generate_content_strategy_report()
        st.download_button(
            "📝 Content Strategy",
            html_content,
            f"content-strategy-{category}.html",
            "text/html",
            use_container_width=True
        )
    
    with col4:
        html_summary = report_gen.generate_executive_summary()
        st.download_button(
            "📋 Resumen Ejecutivo",
            html_summary,
            f"resumen-ejecutivo-{category}.html",
            "text/html",
            use_container_width=True
        )
    
    st.markdown("""
    <div style="background: rgba(0,217,255,0.1); border: 1px solid rgba(0,217,255,0.3); border-radius: 10px; padding: 1rem; margin-top: 1rem;">
        <h4>💡 Sobre los Reportes HTML</h4>
        <p>Cada reporte es un dashboard interactivo autónomo con:</p>
        <ul>
            <li><strong>Gráficos Chart.js</strong> interactivos</li>
            <li><strong>Métricas</strong> calculadas automáticamente</li>
            <li><strong>Insights</strong> específicos de la categoría</li>
            <li><strong>Diseño responsive</strong> para presentaciones</li>
        </ul>
        <p>Abre los archivos HTML en cualquier navegador para ver los dashboards completos.</p>
    </div>
    """, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    init_session_state()
    
    # Header
    st.markdown('<h1 class="main-header">🏗️ Facet Architecture Analyzer</h1>', unsafe_allow_html=True)
    st.markdown('<p style="text-align: center; color: #888;">Análisis UX + SEO para navegación facetada</p>', unsafe_allow_html=True)
    
    # Sidebar
    render_sidebar()
    
    # Tabs
    tabs = st.tabs([
        "📊 Overview",
        "🔄 UX + SEO",
        "🔴 Canibalización",
        "🎯 Gaps",
        "💡 Insights",
        "🚀 Recomendaciones",
        "📥 Exportar"
    ])
    
    with tabs[0]:
        render_overview_tab()
    with tabs[1]:
        render_ux_seo_tab()
    with tabs[2]:
        render_cannibalization_tab()
    with tabs[3]:
        render_gaps_tab()
    with tabs[4]:
        render_insights_tab()
    with tabs[5]:
        render_recommendations_tab()
    with tabs[6]:
        render_export_tab()


if __name__ == "__main__":
    main()
