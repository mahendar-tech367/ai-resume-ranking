import os

from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate

# Load environment variables
load_dotenv()

# Get Groq API key
api_key = os.getenv("GROQ_API_KEY")

if not api_key:
    raise ValueError(
        "GROQ_API_KEY is missing. Check your .env file."
    )

# Connect to Groq
llm = ChatGroq(
    model="openai/gpt-oss-120b",
    temperature=0.7,
    max_retries=2,
    groq_api_key=api_key
)

# ResumeRanker AI Mentor prompt
prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        """
        You are ResumeRanker AI Mentor.

        Help users with:
        - Resume improvement
        - Resume analysis
        - AI/ML career guidance
        - Interview preparation
        - Python and Java programming
        - Project suggestions

        Use simple English.
        Be friendly and practical.
        Give actionable answers.
        Do not invent resume details.
        """
    ),
    ("human", "{user_message}")
])

# Create LangChain chain
chain = prompt | llm


def chat_with_ai(user_message):

    response = chain.invoke({
        "user_message": user_message
    })

    return response.content