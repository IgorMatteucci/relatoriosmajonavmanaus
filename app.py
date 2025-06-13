import streamlit as st
import pandas as pd
from datetime import datetime
import os
import io

# ======= GOOGLE SHEETS (INTEGRAÇÃO) =======
import gspread
from google.oauth2.service_account import Credentials
from gspread_dataframe import set_with_dataframe
def sanitize_number(val):
    try:
        if isinstance(val, str):
            # Remove pontos de milhar e troca vírgula por ponto decimal
            return float(val.replace(".", "").replace(",", "."))
        return float(val)
    except Exception:
        return 0.0


SHEET_URL = "1GwZEeD1Fk4toqIit5qzXyokJzaZRJmH-g47R9JV2jXA"
SHEET_NAME = "registros"

scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

# --- Auxiliares para datas e floats
def parse_date(data_str):
    try:
        if data_str and str(data_str).lower() != "nan":
            return pd.to_datetime(data_str).date()
    except:
        pass
    return datetime.today().date()

def parse_float(valor):
    try:
        return float(str(valor).replace('.', '').replace(',', '.'))
    except:
        return 0.0

# --- Autenticação via st.secrets
creds_dict = dict(st.secrets["gcp_service_account"])
credentials = Credentials.from_service_account_info(creds_dict, scopes=scope)
gc = gspread.authorize(credentials)

def salvar_google_sheets(dados):
    try:
        spreadsheet = gc.open_by_key(SHEET_URL)
        worksheet = spreadsheet.worksheet(SHEET_NAME)
        worksheet.clear()
        set_with_dataframe(worksheet, dados)
    except Exception as e:
        st.warning(f"Não foi possível atualizar Google Sheets: {e}")

# --- Função para sempre ler direto do Google Sheets
def carregar_dados():
    try:
        spreadsheet = gc.open_by_key(SHEET_URL)
        worksheet = spreadsheet.worksheet(SHEET_NAME)
        dados = pd.DataFrame(worksheet.get_all_records())
        # Garante datas em string
        for col in ["data_saida_belem", "data_chegada_manaus", "data_saida_manaus"]:
            if col in dados.columns:
                dados[col] = dados[col].astype(str).replace("NaT", "")
        return dados
    except Exception as e:
        st.warning(f"Erro ao carregar dados do Google Sheets: {e}")
        if os.path.exists("viagens.xlsx"):
            dados = pd.read_excel("viagens.xlsx")
            for col in ["data_saida_belem", "data_chegada_manaus", "data_saida_manaus"]:
                if col in dados.columns:
                    dados[col] = dados[col].astype(str).replace("NaT", "")
            return dados
        else:
            return pd.DataFrame(columns=[
                "id_viagem", "nome_barco", "balsa1", "balsa2",
                "data_saida_belem", "hora_saida_belem", "diesel_abastecido_belem",
                "data_chegada_manaus", "hora_chegada_manaus", "horas_navegadas_balsa", "diesel_chegada_barco",
                "balsa_saida_manaus", "balsa2_saida_manaus",
                "data_saida_manaus", "hora_saida_manaus", "tempo_total_porto",
                "manobras", "mca",
                "saldo_diesel_atual", "abastecimento",
                "transbordo", "qtd_transbordo", "barco_transbordo",
                "saldo_diesel_viagem"
            ])

def salvar_dados(dados):
    dados.to_excel("viagens.xlsx", index=False, engine="openpyxl")

st.set_page_config(page_title="Controle de Viagens", layout="wide")  # PRIMEIRA linha Streamlit

# --- LOGIN ---
USUARIO_CORRETO = "majonavmanaus"
SENHA_CORRETA = "MJNVA1B2C3@"

def login():
    st.title("🔒 Login do Sistema")
    usuario = st.text_input("Usuário")
    senha = st.text_input("Senha", type="password")
    if st.button("Entrar"):
        if usuario == USUARIO_CORRETO and senha == SENHA_CORRETA:
            st.session_state["autenticado"] = True
            st.success("Bem-vindo!")
            st.rerun()
        else:
            st.error("Usuário ou senha incorretos.")

if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False

if not st.session_state["autenticado"]:
    login()
    st.stop()

# --- MENU LATERAL ---
st.sidebar.title("Navegação")
pagina = st.sidebar.radio("Ir para:", ["Cadastro/Editar Viagem", "Registros e Relatórios"])

dados = carregar_dados()

# --- CADASTRO / EDIÇÃO ---
if pagina == "Cadastro/Editar Viagem":
    st.title("📝 Cadastro e Pesquisa de Viagens")
    st.subheader("🔎 Pesquisar Viagem para Editar")
    opcoes_busca = ["id_viagem", "nome_barco"]
    criterio = st.selectbox("Buscar por:", opcoes_busca)
    valor_busca = st.text_input("Digite o valor de busca:")

    indice_editar = None
    dados_encontrados = pd.DataFrame()
    if valor_busca:
        if criterio == "id_viagem":
            dados_encontrados = dados[dados["id_viagem"].astype(str).str.contains(valor_busca, case=False, na=False)]
        else:
            dados_encontrados = dados[dados["nome_barco"].astype(str).str.contains(valor_busca, case=False, na=False)]
    if not dados_encontrados.empty:
        st.write("Viagens encontradas:")
        st.dataframe(dados_encontrados[["id_viagem", "nome_barco", "data_saida_belem", "data_chegada_manaus"]],
                     hide_index=True, use_container_width=True)
        selecao = st.selectbox("Selecione o ID da viagem para editar:", dados_encontrados["id_viagem"].unique())
        indices = dados.index[dados["id_viagem"] == selecao].tolist()
        if indices:
            indice_editar = indices[0]
            registro = dados.loc[indice_editar].to_dict()
            st.info(f"Editando viagem com ID {selecao}")
        else:
            indice_editar = None
            registro = {}
    else:
        registro = {}

    def get_registro(key, default):
        return registro.get(key, default)

    def get_data_or_none(valor):
        if not valor or str(valor).lower() in ("", "nan", "none", "nat"):
            return None
        try:
            return pd.to_datetime(valor).date()
        except:
            return None


    with st.form("form_cadastro"):
    st.header("🚢 Saída de Belém")
    col1, col2 = st.columns(2)
    with col1:
        id_viagem = st.text_input("ID da Viagem", value=str(get_registro("id_viagem", "")))
        nome_barco = st.text_input("Nome do Barco", value=get_registro("nome_barco", ""))
        balsa1 = st.text_input("Nome da Balsa 1", value=get_registro("balsa1", ""))
    with col2:
        balsa2 = st.text_input("Nome da Balsa 2 (opcional)", value=get_registro("balsa2", ""))
        data_saida_belem = st.date_input(
            "Data Saída Belém",
            value=get_data_or_none(get_registro("data_saida_belem", "")),
            key="data_saida_belem"
        )
        hora_saida_belem = st.text_input("Hora Saída Belém (HH:MM)", value=str(get_registro("hora_saida_belem", "")))
        diesel_abastecido_belem = st.number_input("Diesel Abastecido em Belém (L)", min_value=0.0, format="%.0f", value=parse_float(get_registro("diesel_abastecido_belem", 0)))

    st.header("🏁 Chegada Manaus")
    col3, col4 = st.columns(2)
    with col3:
        data_chegada_manaus = st.date_input(
            "Data Chegada Manaus",
            value=get_data_or_none(get_registro("data_chegada_manaus", "")),
            key="data_chegada_manaus"
        )
        hora_chegada_manaus = st.text_input("Hora Chegada Manaus (HH:MM)", value=str(get_registro("hora_chegada_manaus", "")))
    with col4:
        diesel_chegada_barco = st.number_input("Diesel Chegada Barco (L)", min_value=0.0, format="%.0f", value=parse_float(get_registro("diesel_chegada_barco", 0)))

    try:
        dt_saida = datetime.combine(data_saida_belem, datetime.strptime(hora_saida_belem, "%H:%M").time())
        dt_chegada = datetime.combine(data_chegada_manaus, datetime.strptime(hora_chegada_manaus, "%H:%M").time())
        diff = dt_chegada - dt_saida
        horas_navegadas = int(diff.total_seconds() // 3600)
        horas_navegadas_str = f"{horas_navegadas}"
    except:
        horas_navegadas_str = ""
    st.text_input("Horas Navegadas Balsa", value=horas_navegadas_str, disabled=True)

    st.header("⚓ Saída Manaus")
    col5, col6 = st.columns(2)
    with col5:
        balsa_saida_manaus = st.text_input("Balsa Saída Manaus", value=get_registro("balsa_saida_manaus", ""))
        balsa2_saida_manaus = st.text_input("Balsa2 Saída Manaus", value=get_registro("balsa2_saida_manaus", ""))
        data_saida_manaus = st.date_input(
            "Data Saída Manaus",
            value=get_data_or_none(get_registro("data_saida_manaus", "")),
            key="data_saida_manaus"
        )
        hora_saida_manaus = st.text_input("Hora Saída Manaus (HH:MM)", value=str(get_registro("hora_saida_manaus", "")))
        try:
            dt_chegada = datetime.combine(data_chegada_manaus, datetime.strptime(hora_chegada_manaus, "%H:%M").time())
            dt_saida_man = datetime.combine(data_saida_manaus, datetime.strptime(hora_saida_manaus, "%H:%M").time())
            tempo_porto = int((dt_saida_man - dt_chegada).total_seconds() // 3600)
            tempo_porto_str = f"{tempo_porto}"
        except:
            tempo_porto_str = ""
        st.text_input("Tempo Total de Porto", value=tempo_porto_str, disabled=True)
        manobras = st.number_input("Manobras (L)", min_value=0.0, format="%.0f", value=parse_float(get_registro("manobras", 0)))
    with col6:
        mca = st.number_input("MCA (L)", min_value=0.0, format="%.0f", value=parse_float(get_registro("mca", 0)))
        saldo_diesel_atual = st.number_input("Saldo Diesel Atual (L)", min_value=0.0, format="%.0f", value=sanitize_number(get_registro("saldo_diesel_atual", 0)))
        abastecimento = st.number_input("Abastecimento (L)", min_value=0.0, format="%.0f", value=parse_float(get_registro("abastecimento", 0)))
        transbordo = st.selectbox("Transbordo", options=["", "Recebeu", "Passou"], index=["", "Recebeu", "Passou"].index(get_registro("transbordo", "")) if get_registro("transbordo", "") in ["", "Recebeu", "Passou"] else 0)
        qtd_transbordo = st.number_input("Qtd. Transbordo (L)", min_value=0.0, format="%.0f", value=parse_float(get_registro("qtd_transbordo", 0)))
        barco_transbordo = st.text_input("Barco do Transbordo", value=get_registro("barco_transbordo", ""))

    # Cálculo do saldo de diesel para viagem (transbordo é somado se for 'Recebeu')
    saldo_diesel_viagem = saldo_diesel_atual + abastecimento
    if transbordo == "Recebeu":
        saldo_diesel_viagem += qtd_transbordo
    st.text_input("Saldo de Diesel para Viagem (L)", value=f"{saldo_diesel_viagem:.0f}", disabled=True)

    if indice_editar is not None:
        col_salvar, col_excluir = st.columns([2, 1])
        with col_salvar:
            submitted = st.form_submit_button("Salvar atualização")
        with col_excluir:
            excluir = st.form_submit_button("Excluir viagem")
    else:
        submitted = st.form_submit_button("Salvar novo registro")
        excluir = False


    if submitted:
        novo_registro = {
            "id_viagem": id_viagem,
            "nome_barco": nome_barco,
            "balsa1": balsa1,
            "balsa2": balsa2,
            "data_saida_belem": data_saida_belem.strftime("%Y-%m-%d"),
            "hora_saida_belem": hora_saida_belem,
            "diesel_abastecido_belem": diesel_abastecido_belem,
            "data_chegada_manaus": data_chegada_manaus.strftime("%Y-%m-%d"),
            "hora_chegada_manaus": hora_chegada_manaus,
            "horas_navegadas_balsa": horas_navegadas_str,
            "diesel_chegada_barco": diesel_chegada_barco,
            "balsa_saida_manaus": balsa_saida_manaus,
            "balsa2_saida_manaus": balsa2_saida_manaus,
            "data_saida_manaus": data_saida_manaus.strftime("%Y-%m-%d"),
            "hora_saida_manaus": hora_saida_manaus,
            "tempo_total_porto": tempo_porto_str,
            "manobras": manobras,
            "mca": mca,
            "saldo_diesel_atual": saldo_diesel_atual,
            "abastecimento": abastecimento,
            "transbordo": transbordo,
            "qtd_transbordo": qtd_transbordo,
            "barco_transbordo": barco_transbordo,
            "saldo_diesel_viagem": saldo_diesel_viagem
        }
        if indice_editar is not None:
            dados.loc[indice_editar] = novo_registro
            st.success(f"✅ Viagem ID {id_viagem} atualizada com sucesso!")
        else:
            dados = pd.concat([dados, pd.DataFrame([novo_registro])], ignore_index=True)
            st.success("✅ Novo registro salvo com sucesso!")
        salvar_dados(dados)
        salvar_google_sheets(dados)
        st.rerun()

    if indice_editar is not None and excluir:
        dados = dados.drop(indice_editar).reset_index(drop=True)
        salvar_dados(dados)
        salvar_google_sheets(dados)
        st.success(f"🚨 Viagem ID {id_viagem} excluída com sucesso!")
        st.rerun()

# --- REGISTROS / RELATÓRIOS ---
else:
    st.title("📊 Registros de Viagens")
    if dados.empty:
        st.info("Ainda não existem registros salvos.")
    else:
        st.dataframe(dados, use_container_width=True, hide_index=True)
        buffer = io.BytesIO()
        dados.to_excel(buffer, index=False, engine="openpyxl")
        st.download_button(
            label="Baixar registros (.xlsx)",
            data=buffer.getvalue(),
            file_name="viagens.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )