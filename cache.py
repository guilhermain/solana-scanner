"""
Cache de sessão por mint.
Armazena compradores já coletados para evitar rebuscar o mesmo token.
"""
import streamlit as st

CACHE_KEY = "mint_cache"

def get(mint: str):
    cache = st.session_state.get(CACHE_KEY, {})
    return cache.get(mint)  # None se não existe

def set(mint: str, data: dict):
    if CACHE_KEY not in st.session_state:
        st.session_state[CACHE_KEY] = {}
    st.session_state[CACHE_KEY][mint] = data

def clear():
    st.session_state[CACHE_KEY] = {}

def list_cached():
    return list(st.session_state.get(CACHE_KEY, {}).keys())
