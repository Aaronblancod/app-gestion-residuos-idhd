# ----- GF-0657: PORGRAMACIÓN EN SIG (2024) | PROFESOR: MANUEL VARGAS TRABAJO FINAL -----
# ----- ESTUDIANTES AARON BLANCO (B91088) Y ARISTIDES GARCÍA (B73114) -----

# ----- Carga y configuración de los paquetes -----

import streamlit as st
import pandas as pd
import plotly.express as px
import geopandas as gpd
import matplotlib.pyplot as plt
import mapclassify
import numpy as np
import folium
import branca

from io import BytesIO
from os import name
from matplotlib import colors
from folium import Choropleth, Popup, Tooltip, GeoJson, GeoJsonTooltip
from streamlit_folium import folium_static, st_folium
from folium.raster_layers import ImageOverlay
from branca.colormap import LinearColormap, linear

# Configuración de pandas para mostrar separadores de miles, 2 dígitos decimales y evitar la notación científica.
pd.set_option('display.float_format', '{:,.2f}'.format)


# ----- Fuentes de datos -----

#Datos de botaderos
datos_botaderos_idhd = 'datos/botaderos_idhd.csv' 

#Datos espaciales de los botaderos
datos_botaderos_gdf = 'datos/botaderos.gpkg'

#Datos espaciales de las provincias
datos_provincias_gdf = 'datos/provincias.gpkg'

#Datos espaciales de los cantones
datos_cantones_gdf = 'datos/cantones.gpkg'


# ----- Funciones para recuperar los datos -----
# Función para cargar los datos y almacenarlos en caché para mejorar el rendimiento

# Función para cargar los datos csv en un dataframe de pandas
@st.cache_data
def cargar_botaderos_idhd():
    botaderos_idhd = pd.read_csv(datos_botaderos_idhd)
    return botaderos_idhd

# Función para cargar los datos geoespaciales en un geodataframe de geopandas
@st.cache_data
def cargar_botaderos_gdf():
    botaderos_gdf = gpd.read_file(datos_botaderos_gdf)
    return botaderos_gdf

@st.cache_data
def cargar_provincias_gdf():
    provincias_gdf = gpd.read_file(datos_provincias_gdf)
    return provincias_gdf

@st.cache_data
def cargar_cantones_gdf():
    cantones_gdf = gpd.read_file(datos_cantones_gdf)
    return cantones_gdf


# ----- TÍTULO DE LA APLICACIÓN -----
st.title('Gestión y problemáticas en torno a los residuos sólidos en Costa Rica')
st.subheader ('Elaborado por: Aaron Blanco (B91088) y Aristides García (B73114)')


# ----- Carga de datos -----
# Cargar datos de botaderos con IDHD
estado_carga_botaderos_idhd = st.text('Cargando datos de los botaderos y su relación con el Índice de Desarrollo Humano ajustado por Desigualdad (IDHD)...')
botaderos_idhd = cargar_botaderos_idhd()
estado_carga_botaderos_idhd.text('Los datos de los botaderos y su relación con el Índice de Desarrollo Humano ajustado por Desigualdad (IDHD) fueron cargados.')

# Cargar datos geoespcailes de botaderos
estado_carga_botaderos_gdf = st.text('Cargando datos geoespaciales de los botaderos...')
botaderos_gdf = cargar_botaderos_gdf()
estado_carga_botaderos_gdf.text('Los datos geoespaciales de los botaderos fueron cargados.')

# Cargar datos geoespcailes de las provicnias
estado_carga_provincias_gdf = st.text('Cargando datos geoespaciales de las provincias...')
provincias_gdf = cargar_provincias_gdf()
estado_carga_provincias_gdf.text('Los datos geoespaciales de las provincias fueron cargados.')

# Cargar datos geoespcailes de los cantones
estado_carga_cantones_gdf = st.text('Cargando datos geoespaciales de los cantones...')
cantones_gdf = cargar_cantones_gdf()
estado_carga_cantones_gdf.text('Los datos geoespaciales de los cantones fueron cargados.')

# ----- PROCESAMIENTO -----


# ----- procesamiento de los datos  según la selección -----
# Obtener la lista de cantones con IDHD según provincia
lista_provincias = botaderos_idhd['provincia'].unique().tolist()
lista_provincias.sort()

# Añadir la opción "Todas" al inicio de la lista
opciones_provincias = ['Todas'] + lista_provincias

# Crear el selectbox en la barra lateral
provincia_seleccionado = st.sidebar.selectbox(
    'Selecciona una provincia',
    opciones_provincias
)

# ----- Filtrar datos según la selección -----

if provincia_seleccionado != 'Todas':
    # Filtrar los datos para el provincia seleccionado
    botaderos_idhd_filtrados = botaderos_idhd[botaderos_idhd['provincia'] == provincia_seleccionado]
    
    # Obtener el Código de la provincia seleccionada
    codigo_seleccionado = botaderos_idhd_filtrados['cod_provin'].iloc[0]
else:
    # No aplicar filtro
    botaderos_idhd_filtrados = botaderos_idhd.copy()
    codigo_seleccionado = None


# ----- procesamiento de los datos geoespaciales según la selección -----
# Unir los datos del IDHD con el GeoDataFrame de cantones
cantones_gdf_merged = cantones_gdf.merge(
    botaderos_idhd_filtrados, 
    how='inner', 
    left_on='canton', 
    right_on='canton'
)

# Unir los datos de la localización de botaderos con el dataframe filtrado
botaderos_gdf_merged = botaderos_gdf.merge(
    botaderos_idhd_filtrados, 
    how='inner', 
    left_on='canton', 
    right_on='canton'
)

# Filtración de las columnas relevantes del conjunto de datos de botaderos filtrado
columnas_bf = [
    'canton',
    'geometry',
    'tipo_x'
]
botaderos_gdf_merged = botaderos_gdf_merged[columnas_bf]
botaderos_gdf_merged = botaderos_gdf_merged.rename(columns={'tipo_x': 'tipo de botadero'})


# ----- Sección interactiva -----
# ----- Tabla de la selección -----

# Mostrar la tabla
st.subheader('Datos seleccionables sobre la gestión de residuos y su relación con el Índice de Desarrollo Humano ajustado por Desigualdad (IDHD) según provincia')
st.dataframe(botaderos_idhd_filtrados, hide_index=True)


# ----- Gráfico de líneas de la evolución del IDHD en cada cantón que contiene al menos un botadero -----

# Seleccionar las columnas de años
anios = botaderos_idhd_filtrados.columns[3:15]

# Transformar los datos a formato largo
botaderos_idhd_largo = botaderos_idhd_filtrados.melt(
    id_vars=['canton', 'provincia'],
    value_vars=anios,
    var_name='Año',
    value_name='IDHD'
)

# Crear el gráfico de líneas
fig3 = px.line(
    botaderos_idhd_largo,
    x='Año',
    y='IDHD',
    color='canton',
    markers=True,
    #title='Evolución del Índice de Desarrollo Humano ajustado por Desigualdad entre 2010 y 2020 por cantón',
    labels={
        'Año': 'Año',
        'IDHD': 'IDHD',
        'canton': 'Cantón'
    },
    hover_data={
        'canton': True,
        'Año': True,
        'IDHD': ':.4f'
    }
)

# Atributos globales y configurar leyenda
fig3.update_layout(
    #title={'text': 'Evolución del Índice de Desarrollo Humano ajustado por Desigualdad entre 2010 y 2020 por cantón', 'x': 0.5},
    legend_title_text='Cantón',
    xaxis=dict(showgrid=True, gridwidth=0.5, gridcolor='lightgray'),
    yaxis=dict(showgrid=True, gridwidth=0.5, gridcolor='lightgray')
)

# Mostrar el gráfico
st.subheader('Evolución del IDHD por cantón con presencia de botaderos entre 2010 y 2020 por cantón con presencia de botaderos según provincia')
st.plotly_chart(fig3)

# # ----- MAPA SELECCIONADO -----


# # # ----- Mapa interactivo: Cantones con presencia de botaderos y su relación con el IDHD -----

botaderos_gdf_merged = botaderos_gdf_merged.to_crs("EPSG:4326")
provincias_gdf = provincias_gdf.to_crs("EPSG:4326")

# Simplificar geometrías de provincias
provincias_gdf['geometry'] = provincias_gdf['geometry'].simplify(tolerance=0.09, preserve_topology=True)

# Calcular el centro del mapa basado en geometrías transformadas
centro = [
    cantones_gdf_merged.geometry.centroid.y.mean(),
    cantones_gdf_merged.geometry.centroid.x.mean()
]

# ----- Crear el mapa base -----
mapa = folium.Map(
    location=centro,
    zoom_start=9,
    zoomControl=False  # Desactiva los controles de zoom (opcional)
)

# ----- Capa de coropletas: Cantones con IDHD -----
colormap = LinearColormap(
    colors=['red', 'yellow', 'green'],  # Colores desde rojo a verde
    vmin=cantones_gdf_merged['media_IDHD'].min(),  # Valor mínimo
    vmax=cantones_gdf_merged['media_IDHD'].max()   # Valor máximo
)

folium.GeoJson(
    cantones_gdf_merged,
    name="Cantones con la Media IDHD (2010-2020) según provincia",
    style_function=lambda feature: {
        'fillColor': colormap(feature['properties']['media_IDHD']),
        'color': 'black',
        'weight': 1,
        'fillOpacity': 0.7,
    },
    tooltip=GeoJsonTooltip(
        fields=["canton", "media_IDHD"],
        aliases=["Cantón:", "Media IDHD:"],
        localize=True
    )
).add_to(mapa)

# Agregar la leyenda de la paleta de colores
colormap.caption = "Media del IDHD (2010-2020)"
colormap.add_to(mapa)

# ----- Capa base opcional: Esri Satellite -----
esri_satellite = folium.TileLayer(
    tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
    attr='Esri',
    name='Esri Satellite',
    overlay=False,
    control=True
).add_to(mapa)

# ----- Capa de botaderos -----
botaderos_gdf_merged.explore(
    m=mapa,
    name='Localización de los botaderos',
    marker_type='circle',
    marker_kwds={'radius': 200, 'color': 'white'},
    tooltip=['canton', 'tipo de botadero'],
    popup=True
)

# Añadir la capa de provincias utilizando geopandas explore
provincias_gdf.explore(
    m=mapa,  # Mapa base de folium
    name="Provincias",  # Nombre de la capa
    color="grey",  # Color de las líneas de las provincias
    style_kwds={"fillOpacity": 0},  # Transparencia total del relleno
    tooltip='provincia',
    highlight=False,  # Desactivar resaltar al pasar el cursor
    popup=True  # muestra popup al hacer clic
)

# ----- Agregar control de capas -----
folium.LayerControl().add_to(mapa)

# ----- Mostrar el mapa en Streamlit -----
st.subheader('Relación entre los cantones con presencia de botaderos y su promedio del IDHD entre 2010 y 2020 según provincia')
st_folium(mapa, width=700, height=600)