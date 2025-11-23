from fpdf import FPDF
import tempfile
import io
import base64
import io
import requests


# --- CLASSE BASE PARA O PDF ---
class PDF(FPDF):
    def header(self):
        self.set_font("Arial", "B", 12)
        self.cell(0, 10, "Relatório de Viabilidade Solar", 0, 0, "C")
        self.ln(15)

    def footer(self):
        self.set_y(-15)
        self.set_font("Arial", "I", 8)
        self.cell(0, 10, f"Página {self.page_no()}", 0, 0, "C")

    def section_title(self, title):
        self.set_font("Arial", "B", 12)
        self.set_fill_color(230, 230, 230)
        self.cell(0, 8, title, 0, 1, "L", fill=True)
        self.ln(4)

    def section_body(self, body_dict):
        self.set_font("Arial", "", 10)
        for key, value in body_dict.items():
            clean_key = str(key).encode('latin-1', 'replace').decode('latin-1')
            clean_value = str(value).encode('latin-1', 'replace').decode('latin-1')
            # Formata como tabela de duas colunas com borda, seguindo o exemplo do usuário
            self.cell(95, 7, clean_key, border=1)
            self.cell(95, 7, clean_value, border=1)
            self.ln() # Quebra de linha após cada par chave-valor
        self.ln(5)
        
    def create_comparison_table(self, table_data):
        """
        Cria a tabela de Geração vs. Consumo.
        """
        try:
            # Extrai os dados
            meses = table_data['meses']
            geracao = table_data['geracao_kwh']
            consumo = table_data['consumo_kwh']
            header_consumo = table_data['cabecalho_consumo']
            total_geracao = table_data['total_geracao_anual']
            total_consumo = table_data['total_consumo_anual']

            # --- Cabeçalho da Tabela ---
            self.set_font("Arial", "B", 10)
            self.set_fill_color(230, 230, 230) # Cor de fundo do cabeçalho
            col_width = (self.w - 20) / 3 # Largura da página (menos margens) dividida por 3 colunas
            
            self.cell(col_width, 7, "Mês", border=1, fill=True, align='C')
            self.cell(col_width, 7, "Geração Estimada (kWh)", border=1, fill=True, align='C')
            
            # Limpa o cabeçalho de consumo para FPDF
            clean_header_consumo = str(header_consumo).encode('latin-1', 'replace').decode('latin-1')
            self.cell(col_width, 7, clean_header_consumo, border=1, fill=True, align='C')
            self.ln()

            # --- Corpo da Tabela (Meses) ---
            self.set_font("Arial", "", 10)
            for i in range(len(meses)):
                # Limpa strings para FPDF
                clean_mes = str(meses[i]).encode('latin-1', 'replace').decode('latin-1')
                clean_geracao = f"{geracao[i]:,.0f}"
                clean_consumo = f"{consumo[i]:,.0f}"

                self.cell(col_width, 7, clean_mes, border=1, align='C')
                self.cell(col_width, 7, clean_geracao, border=1, align='R') # Alinha números à direita
                self.cell(col_width, 7, clean_consumo, border=1, align='R') # Alinha números à direita
                self.ln()

            # --- Linha de Total Anual ---
            self.set_font("Arial", "B", 10) # Negrito para o total
            self.cell(col_width, 7, "Total Anual", border=1, fill=True, align='C')
            
            clean_total_geracao = f"{total_geracao:,.0f}"
            clean_total_consumo = f"{total_consumo:,.0f}"
            
            self.cell(col_width, 7, clean_total_geracao, border=1, fill=True, align='R')
            self.cell(col_width, 7, clean_total_consumo, border=1, fill=True, align='R')
            self.ln(10) # Espaço extra após a tabela
        except Exception as e:
            self.write_error(f"Erro ao gerar tabela comparativa: {e}")
    # --- FIM DO NOVO MÉTODO ---

    def write_error(self, message):
        self.set_font("Arial", "I", 8)
        self.set_text_color(255, 0, 0)
        self.cell(0, 6, f"Não foi possível gerar o componente: {message}", 0, 1)
        self.set_text_color(0, 0, 0)


# --- FUNÇÃO PARA BAIXAR O MAPA ---
def get_static_map_image(lat, lon):
    try:
        map_url = f"https://static-maps.yandex.ru/1.x/?lang=pt_BR&ll={lon},{lat}&z=12&l=map&size=600,450&pt={lon},{lat},pm2rdl"
        response = requests.get(map_url, timeout=10)
        response.raise_for_status()
        return response.content
    except requests.exceptions.RequestException as e:
        print(f"Erro ao baixar imagem do mapa: {e}")
        return None


# --- FUNÇÃO PRINCIPAL DE CRIAÇÃO DO RELATÓRIO ---
def create_enhanced_pdf_report(data, client_info, lat, lon):
    pdf = PDF()
    pdf.add_page()

    # --- Dados do Cliente ---
    pdf.section_title("Dados do Cliente")
    pdf.section_body(client_info)

    # --- Parâmetros da Simulação ---
    pdf.section_title("Parâmetros da Simulação")
    pdf.set_font("Arial", "", 10)
    for key, value in data['parametros_simulacao'].items():
        clean_key = str(key).encode('latin-1', 'replace').decode('latin-1')
        clean_value = str(value).encode('latin-1', 'replace').decode('latin-1')
        pdf.cell(95, 7, clean_key, border=1)
        pdf.cell(95, 7, clean_value, border=1)
        pdf.ln()
    pdf.ln(5)

    # --- Resumo Geral ---
    pdf.section_title("Resumo Geral do Projeto")
    pdf.section_body(data['resumo_geral'])

    # --- Análise de Investimento ---
    pdf.section_title("Análise de Investimento")
    pdf.section_body(data['analise_investimento'])

    # --- NOVA SEÇÃO: TABELA COMPARATIVA ---
    # Verifica se os dados mensais foram enviados
    if 'dados_mensais' in data and data['dados_mensais']:
        pdf.section_title("Comparativo Geração Estimada vs. Consumo")
        pdf.create_comparison_table(data['dados_mensais'])
    else:
        pdf.write_error("Tabela Comparativa (Dados mensais não encontrados no relatório)")
    pdf.add_page()
    pdf.section_title("Localização do Projeto")
    map_image_bytes = get_static_map_image(lat, lon)
    if map_image_bytes:
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
                tmp.write(map_image_bytes)
                tmp_path = tmp.name

            start_y = pdf.get_y()
            img_width = pdf.w - 20
            img_height = (img_width / 600) * 450

            pdf.image(tmp_path, x=10, y=start_y, w=img_width, h=img_height)
        except Exception as e:
            pdf.write_error(f"Mapa de Localização (Erro ao renderizar imagem): {e}")
    else:
        pdf.write_error("Mapa de Localização (Falha no download da imagem)")

    # --- Finalização e Codificação ---
    pdf_output = pdf.output(dest='S')
    # Compatibilidade entre FPDF 1.x e 2.x
    if isinstance(pdf_output, str):
        pdf_output = pdf_output.encode('latin-1')
    return base64.b64encode(pdf_output).decode('latin-1')