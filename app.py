import os
import logging

import pandas as pd
import matplotlib.pyplot as plt
import streamlit as st
import openai

# --- Setup ---
openai.api_key = os.getenv("OPENAI_API_KEY")
st.set_page_config(page_title="📊 Heineken Financial Analyst", layout="wide")
logging.basicConfig(level=logging.INFO)

# --- Constants ---
DEFAULT_METRICS = ["operating_cash_flow", "net_income"]


# --- Helper Functions ---

def load_data(uploaded_file):
    try:
        df = pd.read_csv(uploaded_file)
        df.columns = [col.strip().lower() for col in df.columns]

        if not {'year', 'metric', 'value'}.issubset(df.columns):
            raise ValueError("CSV must contain 'year', 'metric', and 'value' columns.")

        df['year'] = df['year'].astype(int)
        return df
    except Exception as e:
        st.error(f"❌ Error loading data: {e}")
        logging.exception("Data loading failed")
        return None


def plot_metrics(df, selected_metrics):
    filtered_df = df[df['metric'].isin(selected_metrics)]

    # Handle duplicates
    aggregated = filtered_df.groupby(['year', 'metric'], as_index=False)['value'].sum()

    # Prepare pivot for visualization
    pivot_df = aggregated.pivot(index='year', columns='metric', values='value')

    if pivot_df.isnull().values.any():
        st.warning("Some values were missing and have been forward-filled.")
        pivot_df = pivot_df.ffill().fillna(0)

    fig, ax = plt.subplots(figsize=(10, 6))
    pivot_df.plot(ax=ax)

    ax.set_xticks(pivot_df.index)
    ax.set_xticklabels(pivot_df.index, rotation=45, fontsize=12)
    ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'{int(x)}'))

    ax.set_xlabel("Year")
    ax.set_ylabel("Value")
    ax.set_title("Heineken Financial Metrics Over Time")

    st.pyplot(fig)
    return aggregated


def build_context_data(df):
    context = {
        year: group.set_index('metric')['value'].to_dict()
        for year, group in df.groupby('year')
    }
    full_text = "\n".join(
        f"{year}: {metrics}" for year, metrics in sorted(context.items())
    )
    return context, full_text


def generate_ai_answer(question, context_data, full_data_text):
    year = next((int(word) for word in question.split() if word.isdigit() and int(word) in context_data), None)

    if year:
        data_context = f"The financial data for {year} is:\n{context_data[year]}"
    else:
        data_context = f"Here is 10 years of Heineken's financial data:\n{full_data_text}"

    prompt = f"{data_context}\n\nQuestion: {question}"

    try:
        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": "You are a financial analyst helping interpret Heineken's financial performance and investment trends."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.4,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        st.error(f"❌ OpenAI error: {e}")
        logging.exception("OpenAI API call failed")
        return None


# --- Streamlit App ---

st.title("📊 Heineken Financial Analyst (2014–2024)")
uploaded_file = st.file_uploader("Upload the Heineken CSV file", type=["csv"])

if uploaded_file:
    df = load_data(uploaded_file)
    if df is not None:
        st.success("✅ Data uploaded successfully!")

        # --- Metric Selection ---
        st.subheader("📈 Visualize Metrics Over Time")
        metrics = sorted(df['metric'].unique())
        st.write("Available metrics:", metrics)

        default_selection = [m for m in DEFAULT_METRICS if m in metrics]
        selected_metrics = st.multiselect("Select metrics to plot", metrics, default=default_selection)

        if selected_metrics:
            aggregated_df = plot_metrics(df, selected_metrics)
            context_by_year, context_text = build_context_data(aggregated_df)
        else:
            st.info("ℹ️ Please select at least one metric to visualize.")

        # --- AI Q&A ---
        st.subheader("💬 Ask AI About Heineken's Financials")
        question = st.text_input("Type your question here (e.g. 'What do you think about the 10-year performance?')")

        if question and selected_metrics:
            with st.spinner("Thinking..."):
                answer = generate_ai_answer(question, context_by_year, context_text)
                if answer:
                    st.markdown("### 🧠 Answer from GPT-4o:")
                    st.write(answer)
        elif question:
            st.info("📊 Please select metrics before asking questions.")
else:
    st.info("📥 Please upload a CSV file to get started.")
