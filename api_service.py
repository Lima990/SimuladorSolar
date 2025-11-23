import requests
import streamlit as st

# O "@st.cache_data" é um "otimizador de performance". Ele diz ao Streamlit para guardar o resultado
# desta função em memória. Se a função for chamada de novo com os MESMOS parâmetros (ex: mesma cidade),
# ele usa o resultado guardado em vez de fazer a busca na internet novamente. Isso deixa o app muito mais rápido.
@st.cache_data
def get_coordinates(city):
    """
    Esta função pega o nome de uma cidade e a transforma em coordenadas geográficas (latitude e longitude)
    usando a API gratuita do OpenStreetMap Nominatim.
    """
    url = "https://nominatim.openstreetmap.org/search"  # Endereço da API.
    headers = {'User-Agent': 'SolarViabilityApp/1.5'}  # Uma "etiqueta" para nos identificarmos para a API.
    params = {'q': city, 'format': 'json', 'limit': 1}  # Parâmetros da busca: a cidade, o formato da resposta e queremos apenas 1 resultado.
    
    try:  # Tenta executar o código abaixo.
        response = requests.get(url, headers=headers, params=params, timeout=10  ) # Faz a chamada para a API, com um tempo limite de 10s.
        response.raise_for_status()  # Verifica se a chamada deu algum erro (como erro 404 ou 500).
        data = response.json()  # Converte a resposta (que vem em texto) para um formato que o Python entende.
        if data:  # Se a API retornou algum dado...
            # Retorna a latitude e a longitude do primeiro resultado encontrado.
            return float(data[0]['lat']), float(data[0]['lon'])
        return None, None  # Se não encontrou dados, retorna "Nada".
    except requests.exceptions.RequestException as e:  # Se a tentativa (try) falhou...
        st.error(f"Erro ao buscar coordenadas: {e}")  # Mostra uma mensagem de erro na tela para o usuário.
        return None, None # Retorna "Nada".

@st.cache_data
def get_pvgis_data(lat, lon, perdas):
    """
    Esta função usa as coordenadas (latitude, longitude) e as perdas do sistema para buscar
    dados de irradiação solar e geração de energia da API PVGIS, um serviço da Comissão Europeia.
    """
    url = "https://re.jrc.ec.europa.eu/api/v5_2/PVcalc" # Endereço da API PVGIS.
    # Parâmetros da busca: lat, lon, potência de 1kWp (para referência  ), perdas, formato da resposta, etc.
    params = {'lat': lat, 'lon': lon, 'peakpower': 1, 'loss': perdas, 'outputformat': 'json', 'pvcalculation': 1, 'mounting_system': 'fixed'}
    
    try: # Tenta fazer a chamada à API.
        response = requests.get(url, params=params, timeout=15) # Faz a chamada com tempo limite de 15s.
        response.raise_for_status()  # Verifica se houve erros na chamada.
        return response.json()  # Retorna os dados de geração solar em formato Python.
    except requests.exceptions.RequestException as e: # Se a chamada falhar...
        st.error(f"Falha ao obter dados da API PVGIS: {e}")  # Mostra um erro na tela.
        return None # Retorna "Nada".



























































