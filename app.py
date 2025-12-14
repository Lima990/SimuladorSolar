# --- IMPORTAÇÃO DE BIBLIOTERAS ---
# Aqui, nós trazemos todas as "caixas de ferramentas" que nosso programa vai precisar para funcionar.

import altair as alt  # Usado para criar gráficos bonitos e interativos.
import numpy as np  # Ferramenta poderosa para cálculos matemáticos e manipulação de listas de números.
import numpy_financial as npf  # Uma caixa de ferramentas específica para cálculos financeiros, como VPL e TIR.
import pandas as pd  # Ótimo para organizar e manipular dados em formato de tabelas (chamadas de DataFrames).
import streamlit as st  # A principal ferramenta para construir a interface web do nosso aplicativo (botões, caixas de texto, gráficos, etc.).

# Importações dos novos módulos (Presumindo que api_service e pdf_report existem)
# from api_service import get_coordinates, get_pvgis_data
# from pdf_report import create_enhanced_pdf_report

# --- Funções Mock para Simulação (Remover em ambiente real) ---
def get_coordinates(cidade):
    # Simula a busca de coordenadas
    if "são paulo" in cidade.lower():
        return -23.5505, -46.6333
    return None, None

def get_pvgis_data(lat, lon, perdas_sistema):
    # Simula dados de geração PVGIS (E_m em kWh/kWp)
    meses = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]
    # Dados simulados para E_m (kWh/kWp)
    e_m_data = [100, 110, 130, 140, 150, 120, 115, 125, 135, 145, 120, 105]
    
    # Aplica as perdas do sistema
    fator_perda = 1 - (perdas_sistema / 100)
    e_m_ajustado = [e * fator_perda for e in e_m_data]
    
    return {
        "outputs": {
            "monthly": {
                "fixed": [
                    {"month": i + 1, "E_m": e_m_ajustado[i], "mes": meses[i]}
                    for i, e in enumerate(e_m_ajustado)
                ]
            }
        }
    }

def create_enhanced_pdf_report(full_report_data, client_data, lat, lon):
    # Simula a criação do PDF e retorna um Base64 fictício
    return "JVBERi0xLjQKJcOkw7zXCn..."
# --- Fim das Funções Mock ---


# --- CONFIGURAÇÃO DA PÁGINA ---
# Define as configurações iniciais da página que o usuário verá no navegador.
st.set_page_config(
    page_title="Simulador Solar",  # O título que aparece na aba do navegador.
    page_icon="☀️",  # O pequeno ícone que aparece na aba do navegador.
    layout="wide",  # Faz com que o conteúdo ocupe toda a largura da tela, dando mais espaço.
    initial_sidebar_state="expanded",  # Deixa o menu lateral (sidebar) visível por padrão.
)

# --- MEMÓRIA DA SESSÃO (SESSION STATE) ---
# O "session_state" é como a memória de curto prazo do aplicativo. Ele guarda informações enquanto o usuário
# está com a página aberta. Isso evita que os resultados desapareçam se o usuário mexer em algum controle.

# Se a variável 'show_results' ainda não existe na memória, crie-a com o valor Falso.
# Isso garante que os resultados da simulação só apareçam depois que o usuário clicar no botão.
if "show_results" not in st.session_state:
    st.session_state.show_results = False

# Se a variável 'generate_pdf' ainda não existe na memória, crie-a com o valor Falso.
# Isso controla a exibição do formulário de dados do cliente para o PDF.
if "generate_pdf" not in st.session_state:
    st.session_state.generate_pdf = False

# --- INTERFACE PRINCIPAL DO APLICATIVO ---
# Esta é a parte do código que desenha a tela que o usuário vê.

st.markdown(
    "<h1 style='text-align: center;'>☀️ Simulador de Viabilidade Solar ☀️</h1>",
    unsafe_allow_html=True,
)  # Título principal, centralizado.
st.divider()  # Adiciona uma linha horizontal para separar o conteúdo.

# --- Seção de Coleta de Dados ---
st.header("👇 Preencha os dados para a simulação")

# --- Cartão 1: Informações Essenciais ---
# `st.container(border=True)` cria uma caixa com borda para organizar visualmente os campos.
with st.container(border=True):
    st.subheader("📍 Informações Essenciais")
    col1, col2 = st.columns(2)  # Divide o espaço em duas colunas.
    with col1:  # Conteúdo da primeira coluna.
        cidade = st.text_input(
            "Cidade e Estado ou CEP", "São Paulo, SP", help="Ex: São Paulo, SP ou 01000-001"
        )
        tarifa_energia = st.number_input(
            "Valor da tarifa de energia (R$/kWh)",
            min_value=0.10,
            value=0.95,
            step=0.01,
            format="%.2f",
        )

    with col2:  # Conteúdo da segunda coluna.
        tipo_consumo = st.radio(
            "Como deseja informar o consumo?",
            ("Média Mensal", "Últimos 12 Meses"),
            key="tipo_consumo_radio",
            horizontal=True,
        )

    consumos_mensais = []  # Prepara uma lista vazia para guardar os consumos de cada mês.
    consumo_mensal_kwh = 0  # Prepara uma variável para guardar o consumo médio.

    # Lógica para mostrar os campos de entrada corretos, dependendo da escolha do usuário.
    if tipo_consumo == "Média Mensal":
        consumo_mensal_kwh = st.number_input(
            "Consumo médio mensal (kWh)", min_value=50, value=350, step=10
        )
    else:  # Se o usuário escolheu "Últimos 12 Meses".
        st.markdown("###### Consumo (kWh) de cada mês:")
        meses = [
            "Jan",
            "Fev",
            "Mar",
            "Abr",
            "Mai",
            "Jun",
            "Jul",
            "Ago",
            "Set",
            "Out",
            "Nov",
            "Dez",
        ]
        cols = st.columns(
            6
        )  # Cria 6 colunas para os campos de entrada dos meses, para economizar espaço.
        for i, mes in enumerate(meses):
            with cols[i % 6]:  # Alterna entre as 6 colunas para posicionar os campos.
                consumo_mes = st.number_input(
                    f"{mes}", min_value=0, value=350, step=10, key=f"consumo_{mes}"
                )
                consumos_mensais.append(
                    consumo_mes
                )  # Adiciona o valor digitado à lista.

# --- Cartão 2: Parâmetros de Custo e Geração ---
with st.container(border=True):
    st.subheader("🛠️ Parâmetros de Custo e Geração")
    col3, col4, col5 = st.columns(3)  # Divide em 3 colunas.
    with col3:
        custo_watt_pico_modulo = st.number_input(
            "Custo do kit fotovoltaico (R$/Wp)", 0.50, 3.00, 1.20, 0.05
        )
    with col4:
        custo_bos_watt_pico = st.number_input(
            "Custo do BoS* (R$/Wp)",
            0.80,
            4.00,
            1.60,
            0.05,
            help="*Balance of System: Projeto, estrutura, cabos, etc.",
        )
    with col5:
        tipo_conexao = st.selectbox(
            "Tipo de Conexão", ["Trifásico", "Bifásico", "Monofásico"]
        )

# --- Cartão 3: Parâmetros de Simulação e Financeiros ---
with st.container(border=True):
    st.subheader("📈 Parâmetros de Simulação e Financeiros")
    col6, col7, col8, col9 = st.columns(4) # Adicionando uma coluna para o novo parâmetro
    with col6:
        perdas_sistema = st.slider(
            "Perdas totais do sistema (%)", 5, 25, 14
        )  # Um controle deslizante.
    with col7:
        margem_geracao_percent = st.slider(
            "Margem de segurança na geração (%)", 0, 50, 15
        )
    with col8:
        inflacao_energia = st.slider(
            "Inflação da tarifa de energia (% a.a.)", 1.0, 15.0, 7.0, 0.5
        )
    with col9: # Novo campo para escolha do método de dimensionamento
        metodo_dimensionamento = st.selectbox(
            "Método de Dimensionamento (kWp)",
            ("Pior Mês (Conservador)", "Média Anual (Otimizado)"),
            help="Escolha se o dimensionamento será pelo mês de menor geração ou pela média anual de geração."
        )

# --- Cartão 4: Financiamento ---
with st.container(border=True):
    st.subheader("🏦 Financiamento")
    financiado = st.radio(
        "O projeto será financiado?",
        ("Não", "Sim"),
        horizontal=True,
        key="financiamento_radio",
    )
    valor_entrada = 0.0
    taxa_juros_mensal = 0.0
    prazo_meses = 0
    # Mostra os campos de financiamento apenas se o usuário selecionar "Sim".
    if financiado == "Sim":
        fin_col1, fin_col2, fin_col3 = st.columns(3)
        with fin_col1:
            valor_entrada = st.number_input(
                "Valor da Entrada (R$)", min_value=0.0, value=5000.0, step=500.0
            )
        with fin_col2:
            taxa_juros_mensal = st.number_input(
                "Taxa de Juros (% a.m.)", min_value=0.1, value=1.8, step=0.1
            )
        with fin_col3:
            prazo_meses = st.number_input(
                "Prazo (Meses)", min_value=12, value=60, step=12
            )

# Botão principal para iniciar a simulação.
submit_button = st.button(label="▶️ Iniciar Simulação Completa")

# Se o botão for pressionado, mude o valor na "memória da sessão" para True.
# Isso fará com que o bloco de código de resultados abaixo seja executado.
if submit_button:
    st.session_state.show_results = True

# --- LÓGICA DE EXECUÇÃO E APRESENTAÇÃO DOS RESULTADOS ---
# Este bloco de código só é executado se `st.session_state.show_results` for True.
if st.session_state.show_results:
    # Determina qual valor de consumo usar para os cálculos.
    if consumos_mensais:  # Se o usuário digitou os consumos dos 12 meses...
        consumo_mensal_kwh_calculado = np.mean(consumos_mensais)  # Calcula a média.
    else:  # Senão, usa o valor médio que ele digitou diretamente.
        consumo_mensal_kwh_calculado = consumo_mensal_kwh

    # Validação: Verifica se os campos essenciais foram preenchidos.
    if not cidade or not consumo_mensal_kwh_calculado > 0:
        st.warning("Por favor, preencha a cidade e o consumo para iniciar.")
    else:
        # Busca as coordenadas da cidade informada.
        lat, lon = get_coordinates(cidade)
        if not lat:  # Se não encontrou as coordenadas...
            st.error(f"Coordenadas para '{cidade}' não encontradas.")
        else:  # Se encontrou...
            with st.spinner(
                f"Buscando dados para {cidade} e calculando..."
            ):  # Mostra uma mensagem de "carregando".
                # Busca os dados de geração solar para o local.
                pvgis_data = get_pvgis_data(lat, lon, perdas_sistema)

            if not pvgis_data:  # Se não conseguiu obter os dados...
                st.error("Falha ao obter dados da API PVGIS.")
            else:  # Se tudo deu certo, começam os cálculos!
                # --- CÁLCULOS PRINCIPAIS ---

                # Custo de disponibilidade (taxa mínima) da concessionária.
                mapa_disponibilidade = {
                    "Monofásico": 30,
                    "Bifásico": 50,
                    "Trifásico": 100,
                }  # kWh mínimos por tipo de conexão.
                disponibilidade_kwh = mapa_disponibilidade[tipo_conexao]
                custo_disponibilidade_mensal = disponibilidade_kwh * tarifa_energia

                # Organiza os dados de geração mensal em uma tabela (DataFrame).
                df = pd.DataFrame(pvgis_data["outputs"]["monthly"]["fixed"])
                
                # --- LÓGICA DE DIMENSIONAMENTO ATUALIZADA ---
                # Identifica a geração do pior mês do ano.
                pior_mes_geracao_por_kwp = df["E_m"].min()
                
                # Calcula a geração média mensal por kWp
                media_mensal_geracao_por_kwp = df["E_m"].mean()

                # Define o fator de dimensionamento com base na escolha do usuário
                if metodo_dimensionamento == "Pior Mês (Conservador)":
                    fator_dimensionamento = pior_mes_geracao_por_kwp
                    nome_fator = "Pior Mês"
                else: # Média Anual (Otimizado)
                    fator_dimensionamento = media_mensal_geracao_por_kwp
                    nome_fator = "Média Anual"
                
                # Validação para evitar divisão por zero
                if fator_dimensionamento <= 0:
                    st.error(f"O fator de dimensionamento ({nome_fator}) é zero ou negativo. Verifique os dados de geração.")
                    st.stop() # Sai da execução se o fator for inválido

                # Calcula o consumo que o sistema precisa suprir, incluindo a margem de segurança.
                consumo_desejado_kwh = consumo_mensal_kwh_calculado * (
                    1 + margem_geracao_percent / 100
                )

                # DIMENSIONAMENTO DO SISTEMA: divide a necessidade de geração pelo fator de dimensionamento escolhido.
                tamanho_sistema_kwp = consumo_desejado_kwh / fator_dimensionamento
                # --- FIM DA LÓGICA DE DIMENSIONAMENTO ATUALIZADA ---

                # Calcula a geração mensal estimada com o sistema dimensionado
                df["geracao_estimada_kwh"] = df["E_m"] * tamanho_sistema_kwp

                # Outros cálculos importantes...
                geracao_anual_estimada = df["geracao_estimada_kwh"].sum()
                consumo_anual_total = consumo_mensal_kwh_calculado * 12
                
                # Custo total do sistema
                custo_total_wp = custo_watt_pico_modulo + custo_bos_watt_pico
                custo_estimado_sistema = tamanho_sistema_kwp * 1000 * custo_total_wp
                
                # Cálculo da economia anual líquida (simplificado para o mock)
                economia_bruta_mensal = consumo_mensal_kwh_calculado * tarifa_energia
                economia_anual_liquida = (economia_bruta_mensal * 12) - (custo_disponibilidade_mensal * 12)
                
                # Cálculo do VPL, TIR e Payback (simplificado para o mock)
                # TMA (Taxa Mínima de Atratividade) - Usando uma taxa de juros de mercado como proxy
                tma_anual = 0.08 # 8% a.a.
                
                # Fluxo de caixa (simplificado)
                anos = 25
                fluxo_caixa = [-custo_estimado_sistema]
                for ano in range(1, anos + 1):
                    # Economia anual crescendo com a inflação da energia
                    economia_projetada = economia_anual_liquida * ((1 + inflacao_energia / 100) ** ano)
                    fluxo_caixa.append(economia_projetada)
                
                vpl = npf.npv(tma_anual, fluxo_caixa)
                tir = npf.irr(fluxo_caixa) * 100
                
                # Payback Descontado (simplificado)
                fluxo_acumulado = 0
                payback_descontado_ano = "Não Calculado"
                for i, valor in enumerate(fluxo_caixa):
                    fluxo_acumulado += valor / ((1 + tma_anual) ** i)
                    if fluxo_acumulado >= 0 and payback_descontado_ano == "Não Calculado":
                        payback_descontado_ano = f"Aproximadamente {i} anos"
                        
                # CO2 e Árvores (valores de conversão fictícios)
                fator_co2 = 0.00045 # ton CO2/kWh
                fator_arvore = 0.01 # árvores/kWh
                co2_evitado_ton = geracao_anual_estimada * anos * fator_co2
                arvores_equivalentes = geracao_anual_estimada * anos * fator_arvore
                
                # --- APRESENTAÇÃO DOS RESULTADOS ---
                st.divider()
                st.header("✅ Resultados da Simulação")

                # --- Cartão de Resumo ---
                with st.container(border=True):
                    st.subheader("Sumário do Projeto")
                    col_resumo1, col_resumo2, col_resumo3 = st.columns(3)
                    
                    col_resumo1.metric(
                        "Potência Recomendada",
                        f"{tamanho_sistema_kwp:.2f} kWp",
                        help=f"Dimensionado pelo método: {metodo_dimensionamento}"
                    )
                    col_resumo2.metric(
                        "Custo Estimado do Sistema",
                        f"R$ {custo_estimado_sistema:,.2f}",
                    )
                    col_resumo3.metric(
                        "Geração Anual Estimada",
                        f"{geracao_anual_estimada:,.0f} kWh",
                    )

                # --- Cartão de Análise Financeira ---
                with st.container(border=True):
                    st.subheader("Análise Financeira")
                    col_fin1, col_fin2, col_fin3 = st.columns(3)
                    
                    col_fin1.metric("VPL (Valor Presente Líquido)", f"R$ {vpl:,.2f}")
                    col_fin2.metric("TIR (Taxa Interna de Retorno)", f"{tir:.2f}% a.a.")
                    col_fin3.metric("Payback Descontado", payback_descontado_ano)

                # --- Gráfico de Geração vs Consumo ---
                st.subheader("Gráfico de Geração vs. Consumo")
                
                # Define as cores para o gráfico
                color_scale = alt.Scale(
                    domain=["Geração Estimada", "Consumo Informado", "Consumo Médio"],
                    range=["#FFC300", "#3366CC", "#009933"],
                )

                # Prepara os dados para o gráfico
                df["mes"] = pd.Categorical(
                    df["mes"],
                    categories=[
                        "Jan",
                        "Fev",
                        "Mar",
                        "Abr",
                        "Mai",
                        "Jun",
                        "Jul",
                        "Ago",
                        "Set",
                        "Out",
                        "Nov",
                        "Dez",
                    ],
                    ordered=True,
                )
                df["month"] = df.index + 1 # Adiciona coluna numérica para ordenação

                if consumos_mensais:  # Se o usuário informou os 12 meses.
                    df["consumo_informado_kwh"] = consumos_mensais
                    
                    df_chart = df.melt(
                        id_vars=["mes", "month"],
                        value_vars=["geracao_estimada_kwh", "consumo_informado_kwh"],
                        var_name="Tipo",
                        value_name="Energia (kWh)",
                    )
                    df_chart["Tipo"] = df_chart["Tipo"].map(
                        {
                            "geracao_estimada_kwh": "Geração Estimada",
                            "consumo_informado_kwh": "Consumo Informado",
                        }
                    )

                    generation_chart = (
                        alt.Chart(df_chart)
                        .mark_bar(opacity=0.8)
                        .encode(
                            # 1. No eixo X, colocamos o 'Tipo' (Geração/Consumo) e removemos o rótulo do eixo
                            x=alt.X("Tipo:N", axis=None, title=None),
                            # 2. O eixo Y permanece o mesmo
                            y=alt.Y("Energia (kWh):Q", title="Energia (kWh)"),
                            # 3. A cor permanece a mesma
                            color=alt.Color(
                                "Tipo:N", scale=color_scale, title="Tipo de Energia"
                            ),
                            # 4. Usamos 'column' para criar os grupos de meses
                            column=alt.Column(
                                "mes:N",
                                sort=alt.EncodingSortField(field="month"),
                                title="Mês",
                                # Posiciona o header ('Jan', 'Fev'...) na parte de baixo
                                header=alt.Header(
                                    titleOrient="bottom", labelOrient="bottom"
                                ),
                            ),
                            tooltip=[
                                "mes",
                                "Tipo",
                                alt.Tooltip("Energia (kWh)", format=".0f"),
                            ],
                        )
                        .properties(
                            title="Geração Estimada vs. Consumo Mensal Informado"
                        )
                        .interactive()
                    )  # Permite zoom e pan

                else:  # Se foi informada apenas a média.
                    # 1. Padronize o Dataframe de Geração (df)
                    df_geracao = df.copy()
                    df_geracao["Tipo"] = "Geração Estimada"
                    df_geracao = df_geracao.rename(
                        columns={"geracao_estimada_kwh": "valor_kwh"}
                    )

                    # 2. Crie o Dataframe de Consumo Médio (df_consumo)
                    df_consumo = pd.DataFrame(
                        {
                            "mes": df["mes"],
                            "month": df["month"],
                            "valor_kwh": [consumo_mensal_kwh_calculado] * len(df),
                            "Tipo": ["Consumo Médio"] * len(df),
                        }
                    )
                    
                    # 3. Concatene os dois DataFrames
                    df_final = pd.concat(
                        [
                            df_geracao[["mes", "month", "valor_kwh", "Tipo"]],
                            df_consumo[["mes", "month", "valor_kwh", "Tipo"]],
                        ]
                    )

                    generation_chart = (
                        alt.Chart(df_final)
                        .mark_bar(
                            opacity=0.9
                        )  # Ajustei opacidade para ficar mais nítido
                        .encode(
                            x=alt.X(
                                "mes:N",
                                sort=alt.EncodingSortField(field="month"),
                                title="Mês",
                                axis=alt.Axis(labelAngle=0),
                            ),
                            y=alt.Y("valor_kwh:Q", title="Energia (kWh)"),
                            # O 'color' define a cor baseada no Tipo (Geração vs Consumo)
                            color=alt.Color(
                                "Tipo:N", scale=color_scale, title=None
                            ),
                            # --- O TRUQUE ESTÁ AQUI ---
                            # xOffset desloca a barra baseado no Tipo, colocando-as lado a lado
                            xOffset="Tipo:N",
                            tooltip=[
                                alt.Tooltip("mes", title="Mês"),
                                alt.Tooltip("Tipo", title="Categoria"),
                                alt.Tooltip(
                                    "valor_kwh", format=".0f", title="Energia (kWh)"
                                ),
                            ],
                        )
                        .properties(
                            title="Geração Estimada vs. Consumo Médio Mensal"
                        )
                        .interactive()
                    )

                st.altair_chart(generation_chart, use_container_width=True)

                # --- Geração do PDF ---
                st.divider()
                st.subheader("Gerar Relatório em PDF")
                if st.button("Gerar Relatório PDF"):
                    st.session_state.generate_pdf = (
                        True  # Ativa a exibição do formulário de cliente.
                    )

                if st.session_state.generate_pdf:
                    # `st.form` agrupa vários campos e só envia os dados quando o botão do formulário é clicado.
                    with st.form("client_info_form"):
                        st.write("Insira os dados do cliente para o relatório:")
                        client_name = st.text_input("Nome do Cliente")
                        client_company = st.text_input("Empresa")
                        client_email = st.text_input("Email")
                        client_phone = st.text_input("Telefone")
                        submit_client_info = st.form_submit_button(
                            "Gerar PDF com Dados do Cliente"
                        )

                    if submit_client_info:  # Se o botão do formulário for clicado...
                        client_data = {
                            "Nome": client_name,
                            "Empresa": client_company,
                            "Email": client_email,
                            "Telefone": client_phone,
                        }

                        # Prepara os dados mensais para enviar ao PDF
                        meses_lista = list(df["mes"])
                        geracao_mensal_lista = list(df["geracao_estimada_kwh"])

                        if consumos_mensais:  # Se o usuário inseriu os 12 meses
                            consumo_mensal_lista = consumos_mensais
                            tipo_consumo_pdf = "Consumo Informado (kWh)"
                        else:  # Se o usuário inseriu a média
                            consumo_mensal_lista = [consumo_mensal_kwh_calculado] * 12
                            tipo_consumo_pdf = "Consumo Médio (kWh)"

                        # Junta todos os dados calculados em um único dicionário para passar para a função do PDF.
                        full_report_data = {
                            "parametros_simulacao": {
                                "Cidade": cidade,
                                "Tarifa de Energia (R$/kWh)": f"{tarifa_energia:.2f}",
                                "Consumo Médio Mensal (kWh)": f"{consumo_mensal_kwh_calculado:.0f}",
                                "Custo do Módulo (R$/Wp)": f"{custo_watt_pico_modulo:.2f}",
                                "Custo do BoS (R$/Wp)": f"{custo_bos_watt_pico:.2f}",
                                "Tipo de Conexão": tipo_conexao,
                                "Perdas do Sistema (%)": perdas_sistema,
                                "Margem de Segurança (%)": margem_geracao_percent,
                                "Inflação Energética Anual (%)": f"{inflacao_energia:.1f}",
                                "TMA Anual (%)": f"{tma_anual * 100:.1f}",
                                "Método de Dimensionamento": metodo_dimensionamento, # Adicionado
                            },
                            "resumo_geral": {
                                "Potência Recomendada (kWp)": f"{tamanho_sistema_kwp:.2f}",
                                "Custo Estimado da Instalação (R$)": f"{custo_estimado_sistema:,.2f}",
                                "Geração Anual Estimada (kWh)": f"{geracao_anual_estimada:,.0f}",
                                "Consumo Anual Total (kWh)": f"{consumo_anual_total:,.0f}",
                                "Economia Anual Líquida (R$)": f"{economia_anual_liquida:,.2f}",
                                "CO2 Evitado em 25 anos (ton)": f"{co2_evitado_ton:,.2f}",
                                "Árvores Equivalentes (25 anos)": f"{arvores_equivalentes:,.0f}",
                            },
                            "analise_investimento": {
                                "Valor Presente Líquido (VPL)": f"R$ {vpl:,.2f}",
                                "Taxa Interna de Retorno (TIR)": f"{tir:.2f}% ao ano",
                                "Payback Descontado": payback_descontado_ano,
                            },
                            "dados_mensais": {
                                "meses": meses_lista,
                                "geracao_kwh": geracao_mensal_lista,
                                "consumo_kwh": consumo_mensal_lista,
                                "cabecalho_consumo": tipo_consumo_pdf,  # Nome da coluna de consumo
                                "total_geracao_anual": geracao_anual_estimada,
                                "total_consumo_anual": consumo_anual_total,
                            },
                        }

                        with st.spinner("Gerando relatório completo em PDF..."):
                            # Chama a função que cria o PDF e o codifica em Base64.
                            pdf_base64 = create_enhanced_pdf_report(
                                full_report_data, client_data, lat, lon
                            )
                            # Cria um link de download em HTML.
                            href = f'<a href="data:application/pdf;base64,{pdf_base64}" download="relatorio_viabilidade_solar_{client_name}.pdf">Clique aqui para baixar o Relatório PDF</a>'
                            st.markdown(href, unsafe_allow_html=True)
                            st.success("Relatório PDF gerado com sucesso!")
