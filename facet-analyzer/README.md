# 🏗️ Facet Architecture Analyzer

Herramienta de análisis **UX + SEO** para arquitectura de navegación facetada en ecommerce.

## 🎯 Objetivo Principal

Cruzar datos de **comportamiento interno** (cómo navegan los usuarios) con **demanda externa** (qué buscan en Google) para:

1. **Optimizar UX**: Ordenar facetas según uso real
2. **Maximizar SEO**: Indexar solo URLs con demanda
3. **Eliminar canibalización**: Que artículos no roben tráfico a filtros
4. **Detectar gaps**: Keywords sin filtro dedicado

## 📊 Análisis que realiza

| Análisis | Fuente de Datos | Insight |
|----------|-----------------|---------|
| **Orden de facetas** | Search Filters + Page URL | Qué facetas usar primero en UI |
| **Arquitectura URLs** | Page Full URL | Niveles N0, N1, N2, N3+ y reglas de indexación |
| **Matriz UX+SEO** | Analytics + GSC | Facetas con alto uso pero baja visibilidad |
| **Canibalización** | Top Query por URL | Artículos rankeando para queries transaccionales |
| **Gaps de demanda** | Keyword Research | Keywords sin filtro dedicado |
| **Reglas indexación** | Top Query | Qué URLs indexar/bloquear |

## 🚀 Despliegue

### Streamlit Cloud (Recomendado)

1. Fork este repositorio
2. Ve a [share.streamlit.io](https://share.streamlit.io)
3. Conecta tu GitHub y selecciona el repo
4. Main file: `app.py`

### Local

```bash
pip install -r requirements.txt
streamlit run app.py
```

## 📁 Archivos de Entrada

### Archivos Obligatorios/Recomendados

| Archivo | Formato | Obligatorio | Descripción |
|---------|---------|-------------|-------------|
| **Top Query** | CSV (UTF-8) | ✅ Sí | BigQuery/GSC con `url`, `url_total_clicks`, `top_query` |

### Adobe Analytics - 4 Archivos (Recomendado cargar todos)

La herramienta obtiene el máximo valor cuando se cargan **los 4 archivos de Adobe Analytics**:

| Archivo | Qué aporta |
|---------|------------|
| **Search Filters - Todo tráfico** | Uso de facetas (qué filtran los usuarios): `pulgadas:55`, `marcas:lg`... |
| **Search Filters - SEO** | Mismo análisis pero solo tráfico orgánico |
| **Page Full URL - Todo tráfico** | Arquitectura de URLs: niveles N0, N1, N2, N3+, combinaciones |
| **Page Full URL - SEO** | Comparar distribución UX vs SEO por nivel |

### Archivos Opcionales

| Archivo | Formato | Descripción |
|---------|---------|-------------|
| **GSC Consultas** | CSV (español) | Export de Search Console - Consultas |
| **GSC Páginas** | CSV (español) | Export de Search Console - Páginas |
| **Keyword Research** | CSV/TSV (UTF-16) | Export de Google Keyword Planner |

## 📈 Formatos de Adobe Analytics

### 1. Search Filters
Formato: `faceta:valor,sesiones`

```csv
Search Filters,1015093
pulgadas:55 pulgadas,83429
pulgadas:65 pulgadas,80506
marcas:lg,64556
marcas:samsung,61118
conectividad:smart tv,44992
tipo pantalla:oled,26560
```

**Proporciona:** Uso de cada faceta para determinar el orden óptimo de navegación.

### 2. Page Full URL
Formato: URLs completas con sesiones

```csv
Page Full URL,1237795
https://www.pccomponentes.com/televisores,154105
https://www.pccomponentes.com/televisores/55-pulgadas,45379
https://www.pccomponentes.com/televisores/55-pulgadas/oled,1876
```

**Proporciona:** Arquitectura de URLs por niveles:
- **N0**: `/televisores` (categoría)
- **N1**: `/televisores/55-pulgadas` (1 faceta)
- **N2**: `/televisores/55-pulgadas/oled` (2 facetas)
- **N3+**: Combinaciones de 3+ facetas

## 📐 Arquitectura de Facetas

La app implementa estas reglas:

### Orden de Facetas en URL
```
/categoria/{tamaño}/{tecnología}/{marca}
```
Basado en comportamiento real: Tamaño > Marca > Tecnología > Conectividad

### Reglas de Indexación
| Nivel | Ejemplo | Indexar |
|-------|---------|---------|
| N0 | `/televisores` | ✅ Siempre |
| N1 | `/televisores/55-pulgadas` | ✅ Siempre |
| N2 | `/televisores/55-pulgadas/oled` | ⚠️ Si demanda >200 |
| N3+ | `/televisores/55-pulgadas/oled/samsung` | ❌ Canonical a N2 |
| Sorting | `?order=price` | ❌ Canonical sin param |
| Precio | `?precio=100-500` | ❌ Usar AJAX |

## 💡 Insights Automáticos

La herramienta genera insights cruzando las fuentes:

- **[HIGH] Arquitectura óptima de URLs** - Desde Page Full URL
- **[HIGH] Prioridad de facetas por uso** - Desde Search Filters
- **[MEDIUM] Combinaciones N2 para indexar** - Desde Page Full URL
- **[MEDIUM] Oportunidades SEO en marcas** - Comparando UX vs SEO
- **[LOW] Consistencia entre fuentes** - Validación cruzada

## 📥 Reportes HTML

4 dashboards interactivos exportables:

1. **🏗️ Arquitectura de Facetas** - Niveles N0-N3+, distribución UX vs SEO
2. **🏆 Market Share** - Share por marca, gaps UX-SEO
3. **📝 Content Strategy** - Mapeo artículos→filtros, canibalización
4. **📋 Resumen Ejecutivo** - Todos los insights clave

## 🔑 API Keys (Opcional)

Para validación con **doble pasada crítica**:

- **Solo Anthropic**: Claude hace análisis Y crítica (self-critique)
- **Solo OpenAI**: GPT hace análisis Y crítica (self-critique)  
- **Ambas APIs**: Claude analiza → GPT critica (o viceversa)

## 🔒 Privacidad

- Los datos NO se envían a servidores externos
- Las API keys se usan solo en sesión
- Todo el procesamiento es local
