# --- IMPORTAÇÃO DE BIBLIOTERAS ---
# Aqui, nós trazemos todas as "caixas de ferramentas" que nosso programa vai precisar para funcionar.

import altair as alt  # Usado para criar gráficos bonitos e interativos.
import numpy as np  # Ferramenta poderosa para cálculos matemáticos e manipulação de listas de números.
import numpy_financial as npf  # Uma caixa de ferramentas específica para cálculos financeiros, como VPL e TIR.
import pandas as pd  # Ótimo para organizar e manipular dados em formato de tabelas (chamadas de DataFrames).
import streamlit as st  # A principal ferramenta para construir a interface web do nosso aplicativo (botões, caixas de texto, gráficos, etc.).

# Importações dos novos módulos
from api_service import get_coordinates, get_pvgis_data
from pdf_report import create_enhanced_pdf_report

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
            "Cidade e Estado ou CEP", "", help="Ex: São Paulo, SP ou 01000-001"
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
    col6, col7, col8 = st.columns(3)
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
                # --- CÁLCulos PRINCIPAIS ---

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

                # Identifica a geração do pior mês do ano. O sistema será dimensionado com base nele.
                pior_mes_geracao_por_kwp = df["E_m"].min()

                # Calcula o consumo que o sistema precisa suprir, incluindo a margem de segurança.
                consumo_desejado_kwh = consumo_mensal_kwh_calculado * (
                    1 + margem_geracao_percent / 100
                )

                # DIMENSIONAMENTO DO SISTEMA: divide a necessidade de geração pela capacidade de geração do pior mês.
                tamanho_sistema_kwp = (
                    consumo_desejado_kwh / pior_mes_geracao_por_kwp
                    if pior_mes_geracao_por_kwp > 0
                    else 0
                )

                # Calcula a geração mensal estimada com o sistema dimensionado
                df["geracao_estimada_kwh"] = df["E_m"] * tamanho_sistema_kwp

                # Outros cálculos importantes...
                geracao_anual_estimada = df[
                    "geracao_estimada_kwh"
                ].sum()  # Geração total em um ano.
                custo_total_watt_pico = (
                    custo_watt_pico_modulo + custo_bos_watt_pico
                )  # Custo total por Watt-pico.
                custo_estimado_sistema = (
                    tamanho_sistema_kwp * custo_total_watt_pico * 1000
                )  # Custo total do sistema.
                consumo_anual_total = (
                    sum(consumos_mensais)
                    if consumos_mensais
                    else consumo_mensal_kwh_calculado * 12
                )  # Consumo total no ano.
                energia_economizada_anual = min(
                    geracao_anual_estimada, consumo_anual_total
                )  # A economia é limitada pelo consumo.
                economia_anual_bruta = (
                    energia_economizada_anual * tarifa_energia
                )  # Economia total em R$.
                economia_anual_liquida = economia_anual_bruta - (
                    custo_disponibilidade_mensal * 12
                )  # Desconta a taxa mínima anual.

                st.divider()

                # --- EXIBIÇÃO DOS RESULTADOS ---

                # Cartão 1: Resumo Geral
                with st.container(border=True):
                    st.header("📊 Resumo Geral")
                    resumo_col1, resumo_col2, resumo_col3 = st.columns(3)
                    # st.metric exibe um número de forma destacada.
                    with resumo_col1:
                        st.metric(
                            "Potência Recomendada", f"{tamanho_sistema_kwp:.2f} kWp"
                        )
                    with resumo_col2:
                        st.metric("Custo Estimado", f"R$ {custo_estimado_sistema:,.2f}")
                    with resumo_col3:
                        st.metric("Economia Anual", f"R$ {economia_anual_liquida:,.2f}")

                    st.divider()
                    st.subheader(f"Localização: {cidade}")
                    st.map(
                        pd.DataFrame({"lat": [lat], "lon": [lon]}), zoom=10
                    )  # Mostra um mapa interativo.
                    st.divider()

                    st.subheader("Indicadores Ambientais (25 anos)")
                    co2_evitado_ton = (
                        geracao_anual_estimada * 25 * 0.475
                    ) / 1000  # Fator de conversão padrão.
                    arvores_equivalentes = (
                        co2_evitado_ton * 7.14
                    )  # Fator de conversão padrão.
                    amb_col1, amb_col2 = st.columns(2)
                    with amb_col1:
                        st.metric(
                            "🌳 Árvores Equivalentes", f"{arvores_equivalentes:,.0f}"
                        )
                    with amb_col2:
                        st.metric("💨 CO₂ Evitado", f"{co2_evitado_ton:,.2f} ton")

                # Cartão 2: Análise de Investimento
                with st.container(border=True):
                    st.header("💰 Análise de Investimento")
                    degradacao_paineis_anual = (
                        0.005  # Perda de eficiência dos painéis por ano (0.5%).
                    )
                    prazo_anos = 25  # Vida útil do projeto para análise.

                    # MONTAGEM DO FLUXO DE CAIXA
                    # O fluxo de caixa é uma lista de todas as entradas e saídas de dinheiro ao longo do tempo.

                    if financiado == "Sim":
                        valor_financiado = custo_estimado_sistema - valor_entrada
                        if valor_financiado < 0:
                            valor_financiado = 0
                        # Calcula o valor da parcela mensal do financiamento.
                        parcela_mensal = (
                            npf.pmt(
                                rate=taxa_juros_mensal / 100,
                                nper=prazo_meses,
                                pv=-valor_financiado,
                            )
                            if valor_financiado > 0
                            else 0
                        )
                        st.info(f"**Parcela Mensal: R$ {parcela_mensal:,.2f}**")
                        custo_anual_financiamento = parcela_mensal * 12

                        fluxo_caixa = [
                            -valor_entrada
                        ]  # A primeira saída de dinheiro é a entrada do financiamento.
                        economia_ano_a_ano = economia_anual_liquida
                        # Loop para calcular o fluxo de cada ano.
                        for ano in range(1, prazo_anos + 1):
                            fluxo_ano = economia_ano_a_ano  # A entrada de dinheiro é a economia.
                            if (
                                ano <= prazo_meses / 12
                            ):  # Se ainda estiver pagando o financiamento...
                                fluxo_ano -= custo_anual_financiamento  # Subtrai o custo do financiamento.
                            fluxo_caixa.append(
                                fluxo_ano
                            )  # Adiciona o resultado do ano ao fluxo de caixa.
                            # Atualiza a economia para o próximo ano, aplicando inflação e degradação.
                            economia_ano_a_ano *= (1 + inflacao_energia / 100) * (
                                1 - degradacao_paineis_anual
                            )
                    else:  # Se o pagamento for à vista.
                        fluxo_caixa = [
                            -custo_estimado_sistema
                        ]  # A única saída é o custo total no ano 0.
                        economia_ano_a_ano = economia_anual_liquida
                        for ano in range(1, prazo_anos + 1):
                            fluxo_caixa.append(economia_ano_a_ano)
                            economia_ano_a_ano *= (1 + inflacao_energia / 100) * (
                                1 - degradacao_paineis_anual
                            )

                    # CÁLCULOS FINANCEIROS
                    tma_anual = (
                        st.slider(
                            "Taxa Mínima de Atratividade (TMA % a.a.)",
                            1.0,
                            20.0,
                            10.0,
                            0.5,
                            key="tma_slider",
                        )
                        / 100
                    )
                    # VPL (Valor Presente Líquido): Traz todos os valores do fluxo de caixa para o "dinheiro de hoje". Se for > 0, o projeto é lucrativo.
                    vpl = npf.npv(tma_anual, fluxo_caixa)
                    # TIR (Taxa Interna de Retorno): A taxa de rentabilidade do projeto. Deve ser maior que a TMA.
                    tir = npf.irr(fluxo_caixa) * 100

                    fin_col1, fin_col2 = st.columns(2)
                    with fin_col1:
                        st.metric("Valor Presente Líquido (VPL)", f"R$ {vpl:,.2f}")
                        if vpl > 0:
                            st.success("✅ Viável")
                        else:
                            st.warning("⚠️ Atenção: VPL negativo")
                    with fin_col2:
                        st.metric(
                            "Taxa Interna de Retorno (TIR)",
                            f"{tir:.2f}% a.a.",
                            delta=f"{(tir - tma_anual * 100):.2f} p.p. vs TMA",
                        )
                        if tir > tma_anual * 100:
                            st.success("✅ Viável")
                        else:
                            st.error("❌ Inviável")

                    # Payback Descontado: Em quanto tempo o investimento se paga, considerando a TMA.
                    vpl_anual = [
                        npf.npv(tma_anual, fluxo_caixa[: i + 1])
                        for i in range(len(fluxo_caixa))
                    ]
                    payback_descontado_ano = next(
                        (
                            f"~{ano} anos"
                            for ano, vpl_valor in enumerate(vpl_anual)
                            if vpl_valor > 0
                        ),
                        "Não alcançado",
                    )
                    st.metric("Payback Descontado", payback_descontado_ano)

                    # GERAÇÃO DO GRÁFICO DE VPL
                    df_vpl = pd.DataFrame(
                        {
                            "Ano": list(range(prazo_anos + 1)),
                            "VPL Acumulado (R$)": vpl_anual,
                        }
                    )
                    vpl_chart = (
                        alt.Chart(df_vpl)
                        .mark_area(
                            line={"color": "#1f77b4"},
                            color=alt.Gradient(
                                gradient="linear",
                                stops=[
                                    alt.GradientStop(color="#d62728", offset=0),
                                    alt.GradientStop(color="#2ca02c", offset=1),
                                ],
                                x1=1,
                                x2=1,
                                y1=1,
                                y2=0,
                            ),
                        )
                        .encode(
                            x=alt.X("Ano:O", axis=alt.Axis(labelAngle=0)),
                            y=alt.Y(
                                "VPL Acumulado (R$):Q",
                                title="VPL Acumulado (R$)",
                                axis=alt.Axis(format="~s"),
                            ),
                            tooltip=[
                                "Ano",
                                alt.Tooltip("VPL Acumulado (R$)", format=",.2f"),
                            ],
                        )
                        .properties(title="Evolução do VPL Acumulado")
                    )

                    st.altair_chart(vpl_chart)

                # --- NOVO BLOCO DO GRÁFICO DE GERAÇÃO ---
                # Cartão 3: Geração vs Consumo
                with st.container(border=True):
                    st.header("📈 Geração Estimada vs Consumo Mensal")
                    # df['geracao_estimada_kwh'] já foi calculado acima
                    meses_pt_map = {
                        m + 1: n
                        for m, n in enumerate(
                            [
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
                        )
                    }
                    df["mes"] = df["month"].map(meses_pt_map)

                    # Definição de cores para os gráficos
                    color_scale = alt.Scale(
                        domain=[
                            "Geração Estimada",
                            "Consumo Informado",
                            "Consumo Médio",
                        ],
                        range=["#4c78a8", "#f58518", "#e45756"],
                    )  # Azul, Laranja, Vermelho para distinção

                    # Lógica para criar o gráfico correto dependendo de como o consumo foi informado.
                    if consumos_mensais:
                        df["consumo_informado_kwh"] = consumos_mensais
                        df_chart = df.melt(
                            id_vars=["mes", "month"],
                            value_vars=[
                                "geracao_estimada_kwh",
                                "consumo_informado_kwh",
                            ],
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
                        bar_chart = (
                            alt.Chart(df)
                            .mark_bar(opacity=0.7, color=color_scale.range[0])
                            .encode(  # Cor para Geração Estimada
                                x=alt.X(
                                    "mes:N",
                                    sort=alt.EncodingSortField(field="month"),
                                    title="Mês",
                                    axis=alt.Axis(labelAngle=0),
                                ),
                                y=alt.Y(
                                    "geracao_estimada_kwh:Q", title="Energia (kWh)"
                                ),
                                tooltip=[
                                    alt.Tooltip("mes", title="Geração Estimada"),
                                    alt.Tooltip("geracao_estimada_kwh", format=".0f"),
                                ],
                            )
                            .properties(
                                title="Geração Estimada vs. Consumo Médio Mensal"
                            )
                        )

                        df_regua = pd.DataFrame(
                            {
                                "mes": df["mes"],
                                "month": df["month"],
                                "consumo": [consumo_mensal_kwh_calculado] * len(df),
                                "Tipo": ["Consumo Médio"] * len(df),
                            }
                        )

                        rule_consumo = (
                            alt.Chart(df_regua)
                            .mark_bar(opacity=0.7, color=color_scale.range[0])
                            .encode(
                                x=alt.X(
                                    "mes:N", sort=alt.EncodingSortField(field="month")
                                ),
                                y=alt.Y("consumo:Q"),
                                tooltip=[
                                    alt.Tooltip(
                                        "consumo", format=".0f", title="Consumo Médio"
                                    )
                                ],
                                color=alt.Color(
                                    "Tipo:N", scale=color_scale, title=None
                                ),
                            )
                        )
                        df_geracao = df.copy()
                        df_geracao["Tipo"] = "Geração Estimada"
                        df_geracao = df_geracao.rename(
                            columns={"geracao_estimada_kwh": "valor_kwh"}
                        )

                        # 2. Padronize o Dataframe de Consumo (df_regua)
                        # Você já criou o df_regua no seu código, só precisamos renomear a coluna de valor para igualar
                        df_consumo = df_regua.copy()
                        df_consumo = df_consumo.rename(columns={"consumo": "valor_kwh"})
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

                    # --- INÍCIO DA CORREÇÃO ---
                    # Esta é a linha que alteramos
                    st.altair_chart(generation_chart)
                    # --- FIM DA CORREÇÃO ---

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

                        # --- INÍCIO DA MODIFICAÇÃO ---
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
                            },
                            "resumo_geral": {
                                "Potência Recomendada (kWp)": f"{tamanho_sistema_kwp:.2f}",
                                "Custo Estimado da Instalação (R$)": f"{custo_estimado_sistema:,.2f}",
                                "Geração Anual Estimada (kWh)": f"{geracao_anual_estimada:,.0f}",
                                "Consumo Anual Total (kWh)": f"{consumo_anual_total:,.0f}",  # Adicionado
                                "Economia Anual Líquida (R$)": f"{economia_anual_liquida:,.2f}",
                                "CO2 Evitado em 25 anos (ton)": f"{co2_evitado_ton:,.2f}",
                                "Árvores Equivalentes (25 anos)": f"{arvores_equivalentes:,.0f}",
                            },
                            "analise_investimento": {
                                "Valor Presente Líquido (VPL)": f"R$ {vpl:,.2f}",
                                "Taxa Interna de Retorno (TIR)": f"{tir:.2f}% ao ano",
                                "Payback Descontado": payback_descontado_ano,
                            },
                            # --- NOVO BLOCO DE DADOS ADICIONADO ---
                            "dados_mensais": {
                                "meses": meses_lista,
                                "geracao_kwh": geracao_mensal_lista,
                                "consumo_kwh": consumo_mensal_lista,
                                "cabecalho_consumo": tipo_consumo_pdf,  # Nome da coluna de consumo
                                "total_geracao_anual": geracao_anual_estimada,
                                "total_consumo_anual": consumo_anual_total,
                            },
                        }
                        # --- FIM DA MODIFICAÇÃO ---

                        with st.spinner("Gerando relatório completo em PDF..."):
                            # Chama a função que cria o PDF e o codifica em Base64.
                            pdf_base64 = create_enhanced_pdf_report(
                                full_report_data, client_data, lat, lon
                            )
                            # Cria um link de download em HTML.
                            href = f'<a href="data:application/pdf;base64,{pdf_base64}" download="relatorio_viabilidade_solar_{client_name}.pdf">Clique aqui para baixar o Relatório PDF</a>'
                            st.markdown(href, unsafe_allow_html=True)
                            st.success("Relatório PDF gerado com sucesso!")

