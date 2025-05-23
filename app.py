import streamlit as st
import pandas as pd
from datetime import datetime
import os
import io

# ======= GOOGLE SHEETS (INTEGRAÇÃO) =======
import gspread
from google.oauth2.service_account import Credentials
from gspread_dataframe import set_with_dataframe

SHEET_URL = "1GwZEeD1Fk4toqIit5qzXyokJzaZRJmH-g47R9JV2jXA"
SHEET_NAME = "registros"

scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

# --- Autenticação via st.secrets
creds_dict = dict(st.secrets["gcp_service_account"])
credentials = Credentials.from_service_account_info(creds_dict, scopes=scope)
gc = gspread.authorize(credentials)

def salvar_google_sheets(dados):
    try:
        spreadsheet = gc.open_by_url(SHEET_URL)
        worksheet = spreadsheet.worksheet(SHEET_NAME)
        worksheet.clear()
        set_with_dataframe(worksheet, dados)
    except Exception as e:
        st.warning(f"Não foi possível atualizar Google Sheets: {e}")

# ======= FIM GOOGLE SHEETS =======

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

# --- FUNÇÕES ---
def carregar_dados():
    if os.path.exists("viagens.xlsx"):
        return pd.read_excel("viagens.xlsx")
    else:
        return pd.DataFrame(columns=[
            "id_viagem", "nome_barco", "balsa1", "balsa2",
            "data_saida_belem", "hora_saida_belem", "diesel_abastecido_belem",
            "data_chegada_manaus", "hora_chegada_manaus", "horas_navegadas_balsa", "diesel_chegada_barco",
            "data_saida_manaus", "hora_saida_manaus", "tempo_total_porto",
            "saldo_diesel_atual", "abastecimento", "saldo_diesel_viagem"
        ])

def salvar_dados(dados):
    dados.to_excel("viagens.xlsx", index=False, engine="openpyxl")

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
        indice_editar = dados.index[dados["id_viagem"] == selecao][0]
        st.info(f"Editando viagem com ID {selecao}")
        registro = dados.loc[indice_editar].to_dict()
    else:
        registro = {
            "id_viagem": "",
            "nome_barco": "",
            "balsa1": "",
            "balsa2": "",
            "data_saida_belem": "",
            "hora_saida_belem": "",
            "diesel_abastecido_belem": 0.0,
            "data_chegada_manaus": "",
            "hora_chegada_manaus": "",
            "horas_navegadas_balsa": "",
            "diesel_chegada_barco": 0.0,
            "data_saida_manaus": "",
            "hora_saida_manaus": "",
            "tempo_total_porto": "",
            "saldo_diesel_atual": 0.0,
            "abastecimento": 0.0,
            "saldo_diesel_viagem": 0.0
        }

    with st.form("form_cadastro"):
        st.header("🚢 Saída de Belém")
        col1, col2 = st.columns(2)
        with col1:
            id_viagem = st.text_input("ID da Viagem", value=str(registro["id_viagem"]))
            nome_barco = st.text_input("Nome do Barco", value=registro["nome_barco"])
            balsa1 = st.text_input("Nome da Balsa 1", value=registro["balsa1"])
        with col2:
            balsa2 = st.text_input("Nome da Balsa 2 (opcional)", value=registro["balsa2"])
            data_saida_belem = st.date_input("Data Saída Belém", value=pd.to_datetime(registro["data_saida_belem"]) if registro["data_saida_belem"] else datetime.today())
            hora_saida_belem = st.time_input("Hora Saída Belém", value=pd.to_datetime(registro["hora_saida_belem"]).time() if registro["hora_saida_belem"] else datetime.now().time())
            diesel_abastecido_belem = st.number_input("Diesel Abastecido em Belém (L)", min_value=0.0, format="%.2f", value=float(registro["diesel_abastecido_belem"]))

        st.header("🏁 Chegada Manaus")
        col3, col4 = st.columns(2)
        with col3:
            data_chegada_manaus = st.date_input("Data Chegada Manaus", value=pd.to_datetime(registro["data_chegada_manaus"]) if registro["data_chegada_manaus"] else datetime.today())
            hora_chegada_manaus = st.time_input("Hora Chegada Manaus", value=pd.to_datetime(registro["hora_chegada_manaus"]).time() if registro["hora_chegada_manaus"] else datetime.now().time())
        with col4:
            diesel_chegada_barco = st.number_input("Diesel Chegada Barco (L)", min_value=0.0, format="%.2f", value=float(registro["diesel_chegada_barco"]))

        try:
            dt_saida = datetime.combine(data_saida_belem, hora_saida_belem)
            dt_chegada = datetime.combine(data_chegada_manaus, hora_chegada_manaus)
            diff = dt_chegada - dt_saida
            horas_navegadas = int(diff.total_seconds() // 3600)
            horas_navegadas_str = f"{horas_navegadas}"
        except:
            horas_navegadas_str = ""
        st.text_input("Horas Navegadas Balsa", value=horas_navegadas_str, disabled=True)

        st.header("⚓ Saída Manaus")
        col5, col6 = st.columns(2)
        with col5:
            data_saida_manaus = st.date_input("Data Saída Manaus", value=pd.to_datetime(registro["data_saida_manaus"]) if registro["data_saida_manaus"] else datetime.today())
            hora_saida_manaus = st.time_input("Hora Saída Manaus", value=pd.to_datetime(registro["hora_saida_manaus"]).time() if registro["hora_saida_manaus"] else datetime.now().time())
        with col6:
            saldo_diesel_atual = st.number_input("Saldo Diesel Atual (L)", min_value=0.0, format="%.2f", value=float(registro["saldo_diesel_atual"]))
            abastecimento = st.number_input("Abastecimento (L)", min_value=0.0, format="%.2f", value=float(registro["abastecimento"]))

        saldo_diesel_viagem = saldo_diesel_atual + abastecimento
        st.text_input("Saldo de Diesel para Viagem (L)", value=f"{saldo_diesel_viagem:.2f}", disabled=True)

        try:
            dt_chegada = datetime.combine(data_chegada_manaus, hora_chegada_manaus)
            dt_saida_man = datetime.combine(data_saida_manaus, hora_saida_manaus)
            tempo_porto = int((dt_saida_man - dt_chegada).total_seconds() // 3600)
            tempo_porto_str = f"{tempo_porto}"
        except:
            tempo_porto_str = ""
        st.text_input("Tempo Total de Porto", value=tempo_porto_str, disabled=True)

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
            "hora_saida_belem": hora_saida_belem.strftime("%H:%M"),
            "diesel_abastecido_belem": diesel_abastecido_belem,
            "data_chegada_manaus": data_chegada_manaus.strftime("%Y-%m-%d"),
            "hora_chegada_manaus": hora_chegada_manaus.strftime("%H:%M"),
            "horas_navegadas_balsa": horas_navegadas_str,
            "diesel_chegada_barco": diesel_chegada_barco,
            "data_saida_manaus": data_saida_manaus.strftime("%Y-%m-%d"),
            "hora_saida_manaus": hora_saida_manaus.strftime("%H:%M"),
            "tempo_total_porto": tempo_porto_str,
            "saldo_diesel_atual": saldo_diesel_atual,
            "abastecimento": abastecimento,
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
