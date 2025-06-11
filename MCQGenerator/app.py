import streamlit as st

st.title("تطبيقي الأول بـ Streamlit")
st.write("مرحبًا! هذا نص يظهر على الواجهة.")
x = st.slider("اختر رقمًا", 0, 100, 50)
st.write("الرقم المختار هو:", x)
