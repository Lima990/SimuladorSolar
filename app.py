# --- IMPORTAÇÃO DE BIBLIOTECAS ---
import altair as alt
import numpy as np
import numpy_financial as npf
import pandas as pd
import streamlit as st

# Importações dos módulos (certifique-se que os arquivos existem na mesma pasta)
from api_service import get_coordinates, get_pvgis_data
from pdf_report import create_enhanced_pdf_report

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="Simulador Solar",
    page_icon="☀️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- MEMÓRIA DA SESSÃO (SESSION STATE) ---
if "show_results" not in st.session_state:
    st.session_state.show_results = False

if "generate_pdf" not in st.session_state:
    st.session_state.generate_pdf = False

# --- INTERFACE PRINCIPAL DO APLICATIVO ---
st.markdown(
    "<h1 style='text-align: center;'>☀️ Simulador de Viabilidade Solar ☀️</h1>",
    unsafe_allow_html=True,
)
st.divider()

# --- Seção de Coleta de Dados ---
st.header("👇 Preencha os dados para a simulação")

# --- Cartão 1: Informações Essenciais ---
with st.container(border=True):
    st.subheader("📍 Informações Essenciais")
    col1, col2 = st.columns(2)
    with col1:
        cidade = st.text_input(
            "Cidade e Estado, CEP ou Latitude e Longitude", "", help="Ex: São Paulo, SP, 01000-001, ou -23.55,-46.63."
        )
        tarifa_energia = st.number_input(
            "Valor da tarifa de energia (R$/kWh)",
            help="Valor somado da Tarifa de Energia (TE), Tarifa de Uso do Sistema de Distribuição (TUSD) e demais Tributos e Encargos.",
            min_value=0.10,
            value=1.00,
            step=0.01,
            format="%.2f",
        )

    with col2:
        tipo_consumo = st.radio(
            "Como deseja informar o consumo?",
            ("Média Mensal", "Últimos 12 Meses"),
            key="tipo_consumo_radio",
            horizontal=True,
        )

    consumos_mensais = []
    consumo_mensal_kwh = 0

    if tipo_consumo == "Média Mensal":
        consumo_mensal_kwh = st.number_input(
            "Consumo médio mensal (kWh)", min_value=50, value=500, step=10
        )
    else:
        st.markdown("###### Consumo (kWh) de cada mês:")
        meses = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]
        cols = st.columns(6)
        for i, mes in enumerate(meses):
            with cols[i % 6]:
                consumo_mes = st.number_input(
                    f"{mes}", min_value=0, value=500, step=10, key=f"consumo_{mes}"
                )
                consumos_mensais.append(consumo_mes)

# --- Cartão 2: Parâmetros de Custo e Geração ---
with st.container(border=True):
    st.subheader("🛠️ Parâmetros de Custo e Geração")
    col3, col4, col5 = st.columns(3)
    with col3:
        custo_watt_pico_modulo = st.number_input(
            "Custo do kit fotovoltaico (R$/Wp)", 
            0.50, 
            4.00, 
            1.00,
            0.05,
            help="Kit fotovoltaico: Placas, Inversor, Estrutura, Cabeamento solar, Conectores MC4."
        )
    with col4:
        custo_bos_watt_pico = st.number_input(
            "Custo do BoS* (R$/Wp)",
            0.50,
            4.00,
            1.00,
            0.05,
            help="*Balance of System: Projeto, Instalação, Cabeamento CA, Disjuntor, DPS, etc.",
        )
    with col5:
        tipo_conexao = st.selectbox(
            "Tipo de Conexão", ["Trifásico", "Bifásico", "Monofásico"]
        )

# --- Cartão 3: Parâmetros de Simulação e Financeiros ---
with st.container(border=True):
    st.subheader("📈 Parâmetros de Simulação e Financeiros")
    
    st.markdown("**Critério de Dimensionamento:**")
    metodo_dimensionamento = st.radio(
        "Definir tamanho do sistema (kWp) baseando-se em:",
        ("Média Anual de Geração", "Pior Mês de Geração"),
        horizontal=True,
        help="Média Anual: Otimiza o ROI (Gera créditos no verão para usar no inverno). Pior Mês: Sistema maior, garante a meta mesmo no inverno."
    )
    st.divider()

    col6, col7, col8 = st.columns(3)
    with col6:
        # Ajustei valor padrão para 15% (mais realista que 0)
        perdas_sistema = st.slider(
            "Perdas totais do sistema (%)", 0, 30, 15
        )
    with col7:
        # Ajustei valor padrão para 10%
        margem_geracao_percent = st.slider(
            "Margem de segurança na geração (%)", 0, 50, 10
        )
    with col8:
        # Ajustei valor padrão para 6% (IPCA energia histórico)
        inflacao_energia = st.slider(
            "Inflação da tarifa de energia (% a.a.)", 0.0, 15.0, 6.0, 0.5
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
    if financiado == "Sim":
        fin_col1, fin_col2, fin_col3 = st.columns(3)
        with fin_col1:
            valor_entrada = st.number_input(
                "Valor da Entrada (R$)", min_value=0.0, value=0.0, step=500.0
            )
        with fin_col2:
            # CORREÇÃO: O value deve ser >= min_value. Mudei de 0 para 1.5
            taxa_juros_mensal = st.number_input(
                "Taxa de Juros (% a.m.)", min_value=0.1, value=1.5, step=0.1
            )
        with fin_col3:
            # CORREÇÃO: O value deve ser >= min_value. Mudei de 0 para 60
            prazo_meses = st.number_input(
                "Prazo (Meses)", min_value=12, value=60, step=12
            )

submit_button = st.button(label="▶️ Iniciar Simulação Completa")

if submit_button:
    st.session_state.show_results = True

# --- LÓGICA DE EXECUÇÃO ---
if st.session_state.show_results:
    if consumos_mensais:
        consumo_mensal_kwh_calculado = np.mean(consumos_mensais)
    else:
        consumo_mensal_kwh_calculado = consumo_mensal_kwh

    if not cidade or not consumo_mensal_kwh_calculado > 0:
        st.warning("Por favor, preencha a cidade e o consumo para iniciar.")
    else:
        lat, lon = get_coordinates(cidade)
        if not lat:
            st.error(f"Coordenadas para '{cidade}' não encontradas.")
        else:
            with st.spinner(f"Buscando dados para {cidade} e calculando..."):
                pvgis_data = get_pvgis_data(lat, lon, perdas_sistema)

            if not pvgis_data:
                st.error("Falha ao obter dados da API PVGIS.")
            else:
                # --- CÁLCULOS PRINCIPAIS ---

                mapa_disponibilidade = {
                    "Monofásico": 30,
                    "Bifásico": 50,
                    "Trifásico": 100,
                }
                
                disponibilidade_kwh = mapa_disponibilidade[tipo_conexao]
                custo_disponibilidade_mensal = disponibilidade_kwh * tarifa_energia

                df = pd.DataFrame(pvgis_data["outputs"]["monthly"]["fixed"])

                fator_geracao_pior_mes = df["E_m"].min()
                fator_geracao_media = df["E_m"].mean()

                if metodo_dimensionamento == "Pior Mês de Geração":
                    fator_dimensionamento = fator_geracao_pior_mes
                else:
                    fator_dimensionamento = fator_geracao_media

                consumo_desejado_kwh = consumo_mensal_kwh_calculado * (
                    1 + margem_geracao_percent / 100
                )

                tamanho_sistema_kwp = (
                    consumo_desejado_kwh / fator_dimensionamento
                    if fator_dimensionamento > 0
                    else 0
                )

                df["geracao_estimada_kwh"] = df["E_m"] * tamanho_sistema_kwp

                geracao_anual_estimada = df["geracao_estimada_kwh"].sum()
                custo_total_watt_pico = custo_watt_pico_modulo + custo_bos_watt_pico
                custo_estimado_sistema = tamanho_sistema_kwp * custo_total_watt_pico * 1000
                
                consumo_anual_total = (
                    sum(consumos_mensais)
                    if consumos_mensais
                    else consumo_mensal_kwh_calculado * 12
                )
                
                energia_economizada_anual = min(geracao_anual_estimada, consumo_anual_total)
                economia_anual_bruta = energia_economizada_anual * tarifa_energia
                economia_anual_liquida = economia_anual_bruta - (custo_disponibilidade_mensal * 12)

                st.divider()

                # --- EXIBIÇÃO DOS RESULTADOS ---
                with st.container(border=True):
                    st.header("📊 Resumo Geral")
                    st.info(f"Dimensionamento calculado pela: **{metodo_dimensionamento}**")
                    resumo_col1, resumo_col2, resumo_col3 = st.columns(3)
                    with resumo_col1:
                        st.metric("Potência Recomendada", f"{tamanho_sistema_kwp:.2f} kWp")
                    with resumo_col2:
                        st.metric("Custo Estimado", f"R$ {custo_estimado_sistema:,.2f}")
                    with resumo_col3:
                        st.metric("Economia Anual", f"R$ {economia_anual_liquida:,.2f}")

                    st.divider()
                    st.subheader(f"Localização: {cidade}")
                    st.map(pd.DataFrame({"lat": [lat], "lon": [lon]}), zoom=10)
                    st.divider()

                    st.subheader("Indicadores Ambientais (25 anos)")
                    co2_evitado_ton = (geracao_anual_estimada * 25 * 0.475) / 1000
                    arvores_equivalentes = co2_evitado_ton * 7.14
                    amb_col1, amb_col2 = st.columns(2)
                    with amb_col1:
                        st.metric("🌳 Árvores Equivalentes", f"{arvores_equivalentes:,.0f}")
                    with amb_col2:
                        st.metric("💨 CO₂ Evitado", f"{co2_evitado_ton:,.2f} ton")

                with st.container(border=True):
                    st.header("💰 Análise de Investimento")
                    degradacao_paineis_anual = 0.005
                    prazo_anos = 25

                    if financiado == "Sim":
                        valor_financiado = custo_estimado_sistema - valor_entrada
                        if valor_financiado < 0:
                            valor_financiado = 0
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

                        fluxo_caixa = [-valor_entrada]
                        economia_ano_a_ano = economia_anual_liquida
                        for ano in range(1, prazo_anos + 1):
                            fluxo_ano = economia_ano_a_ano
                            if ano <= prazo_meses / 12:
                                fluxo_ano -= custo_anual_financiamento
                            fluxo_caixa.append(fluxo_ano)
                            economia_ano_a_ano *= (1 + inflacao_energia / 100) * (1 - degradacao_paineis_anual)
                    else:
                        fluxo_caixa = [-custo_estimado_sistema]
                        economia_ano_a_ano = economia_anual_liquida
                        for ano in range(1, prazo_anos + 1):
                            fluxo_caixa.append(economia_ano_a_ano)
                            economia_ano_a_ano *= (1 + inflacao_energia / 100) * (1 - degradacao_paineis_anual)

                    tma_anual = st.slider(
                        "Taxa Mínima de Atratividade (TMA % a.a.)",
                        1.0, 20.0, 10.0, 0.5, key="tma_slider"
                    ) / 100
                    
                    vpl = npf.npv(tma_anual, fluxo_caixa)
                    tir = npf.irr(fluxo_caixa) * 100

                    fin_col1, fin_col2 = st.columns(2)
                    with fin_col1:
                        st.metric("Valor Presente Líquido (VPL)", f"R$ {vpl:,.2f}")
                        if vpl > 0:
                            st.success("✅ Viável")
                        else:
                            st.warning("⚠️ Atenção: VPL negativo")
                    with fin_col2:
                        st.metric("Taxa Interna de Retorno (TIR)", f"{tir:.2f}% a.a.", delta=f"{(tir - tma_anual * 100):.2f} p.p. vs TMA")
                        if tir > tma_anual * 100:
                            st.success("✅ Viável")
                        else:
                            st.error("❌ Inviável")

                    vpl_anual = [npf.npv(tma_anual, fluxo_caixa[: i + 1]) for i in range(len(fluxo_caixa))]
                    payback_descontado_ano = next((f"~{ano} anos" for ano, vpl_valor in enumerate(vpl_anual) if vpl_valor > 0), "Não alcançado")
                    st.metric("Payback Descontado", payback_descontado_ano)

                    df_vpl = pd.DataFrame({"Ano": list(range(prazo_anos + 1)), "VPL Acumulado (R$)": vpl_anual})
                    vpl_chart = (
                        alt.Chart(df_vpl)
                        .mark_area(line={"color": "#1f77b4"}, color=alt.Gradient(gradient="linear", stops=[alt.GradientStop(color="#d62728", offset=0), alt.GradientStop(color="#2ca02c", offset=1)], x1=1, x2=1, y1=1, y2=0))
                        .encode(
                            x=alt.X("Ano:O", axis=alt.Axis(labelAngle=0)),
                            y=alt.Y("VPL Acumulado (R$):Q", title="VPL Acumulado (R$)", axis=alt.Axis(format="~s")),
                            tooltip=["Ano", alt.Tooltip("VPL Acumulado (R$)", format=",.2f")]
                        )
                        .properties(title="Evolução do VPL Acumulado")
                    )
                    st.altair_chart(vpl_chart)

                with st.container(border=True):
                    st.header("📈 Geração Estimada vs Consumo Mensal")
                    meses_pt_map = {m + 1: n for m, n in enumerate(["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"])}
                    df["mes"] = df["month"].map(meses_pt_map)
                    color_scale = alt.Scale(domain=["Geração Estimada", "Consumo Informado", "Consumo Médio"], range=["#4c78a8", "#f58518", "#e45756"])

                    if consumos_mensais:
                        df["consumo_informado_kwh"] = consumos_mensais
                        df_chart = df.melt(id_vars=["mes", "month"], value_vars=["geracao_estimada_kwh", "consumo_informado_kwh"], var_name="Tipo", value_name="Energia (kWh)")
                        df_chart["Tipo"] = df_chart["Tipo"].map({"geracao_estimada_kwh": "Geração Estimada", "consumo_informado_kwh": "Consumo Informado"})
                        generation_chart = (
                            alt.Chart(df_chart)
                            .mark_bar(opacity=0.8)
                            .encode(
                                x=alt.X("Tipo:N", axis=None, title=None),
                                y=alt.Y("Energia (kWh):Q", title="Energia (kWh)"),
                                color=alt.Color("Tipo:N", scale=color_scale, title="Tipo de Energia"),
                                column=alt.Column("mes:N", sort=alt.EncodingSortField(field="month"), title="Mês", header=alt.Header(titleOrient="bottom", labelOrient="bottom")),
                                tooltip=["mes", "Tipo", alt.Tooltip("Energia (kWh)", format=".0f")]
                            )
                            .properties(title="Geração Estimada vs. Consumo Mensal Informado")
                            .interactive()
                        )
                    else:
                        df_geracao = df.copy()
                        df_geracao["Tipo"] = "Geração Estimada"
                        df_geracao = df_geracao.rename(columns={"geracao_estimada_kwh": "valor_kwh"})
                        
                        df_consumo = pd.DataFrame({
                            "mes": df["mes"],
                            "month": df["month"],
                            "valor_kwh": [consumo_mensal_kwh_calculado] * len(df),
                            "Tipo": ["Consumo Médio"] * len(df)
                        })
                        
                        df_final = pd.concat([df_geracao[["mes", "month", "valor_kwh", "Tipo"]], df_consumo[["mes", "month", "valor_kwh", "Tipo"]]])
                        
                        generation_chart = (
                            alt.Chart(df_final)
                            .mark_bar(opacity=0.9)
                            .encode(
                                x=alt.X("mes:N", sort=alt.EncodingSortField(field="month"), title="Mês", axis=alt.Axis(labelAngle=0)),
                                y=alt.Y("valor_kwh:Q", title="Energia (kWh)"),
                                color=alt.Color("Tipo:N", scale=color_scale, title=None),
                                xOffset="Tipo:N",
                                tooltip=[alt.Tooltip("mes", title="Mês"), alt.Tooltip("Tipo", title="Categoria"), alt.Tooltip("valor_kwh", format=".0f", title="Energia (kWh)")]
                            )
                            .properties(title="Geração Estimada vs. Consumo Médio Mensal")
                            .interactive()
                        )

                    st.altair_chart(generation_chart)

                st.divider()
                st.subheader("Gerar Relatório em PDF")
                if st.button("Gerar Relatório PDF"):
                    st.session_state.generate_pdf = True

                if st.session_state.generate_pdf:
                    with st.form("client_info_form"):
                        st.write("Insira os dados do cliente para o relatório:")
                        client_name = st.text_input("Nome do Cliente")
                        client_company = st.text_input("Empresa")
                        client_email = st.text_input("Email")
                        client_phone = st.text_input("Telefone")
                        submit_client_info = st.form_submit_button("Gerar PDF com Dados do Cliente")

                    if submit_client_info:
                        client_data = {"Nome": client_name, "Empresa": client_company, "Email": client_email, "Telefone": client_phone}
                        meses_lista = list(df["mes"])
                        geracao_mensal_lista = list(df["geracao_estimada_kwh"])
                        if consumos_mensais:
                            consumo_mensal_lista = consumos_mensais
                            tipo_consumo_pdf = "Consumo Informado (kWh)"
                        else:
                            consumo_mensal_lista = [consumo_mensal_kwh_calculado] * 12
                            tipo_consumo_pdf = "Consumo Médio (kWh)"

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
                                "Dimensionamento": metodo_dimensionamento,
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
                                "cabecalho_consumo": tipo_consumo_pdf,
                                "total_geracao_anual": geracao_anual_estimada,
                                "total_consumo_anual": consumo_anual_total,
                            },
                        }
                        
                        with st.spinner("Gerando relatório completo em PDF..."):
                            pdf_base64 = create_enhanced_pdf_report(full_report_data, client_data, lat, lon)
                            href = f'<a href="data:application/pdf;base64,{pdf_base64}" download="relatorio_viabilidade_solar_{client_name}.pdf">Clique aqui para baixar o Relatório PDF</a>'
                            st.markdown(href, unsafe_allow_html=True)
                            st.success("Relatório PDF gerado com sucesso!")


