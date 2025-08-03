import pandas as pd
import numpy as np
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain.chains.retrieval import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.embeddings import Embeddings
import requests
from tqdm import tqdm 


class SiliconFlowEmbeddings(Embeddings):
    def __init__(self, api_key: str, model_name: str = "BAAI/bge-large-zh-v1.5"):
        """
        初始化嵌入类。
        :param api_key: 你在硅基流动平台的 API 密钥
        :param model_name: 你使用的模型名称，默认为 'BAAI/bge-large-zh-v1.5'
        """
        self.api_key = "sk-cwonxmmcrmzdzpgmoomlagrhupjsyfrwfzhoipbcuvhaeplj"
        self.model_name = "BAAI/bge-large-en-v1.5"
        self.url = "https://api.siliconflow.cn/v1/embeddings"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    def embed_documents(self, texts):
        """
        为文档列表生成嵌入向量。
        :param texts: 文档内容列表
        :return: 嵌入向量列表
        """
        embeddings = []
        for text in tqdm(texts):
            payload = {
                "model": self.model_name,
                "input": text
            }
            response = requests.post(self.url, json=payload, headers=self.headers)
            # print(response.json()["data"][0]["embedding"])
            if response.status_code == 200:
                embeddings.append(response.json()["data"][0]["embedding"])
            else:
                print(f"Error: {response.status_code} - {response.text}")
                # 在错误时添加一个默认的零向量
                embeddings.append([0.0] * 1024)  # 假设嵌入向量大小为 1024
                
        return embeddings

    def embed_query(self, text):
        """
        为单个查询生成嵌入向量。
        :param text: 查询文本
        :return: 单个查询的嵌入向量
        """
        return self.embed_documents([text])[0]  # 仅返回单个查询的嵌入向量


# 文件加载并处理
def load_and_process_pdf(file_path):
    loader = PyPDFLoader(file_path)
    docs = loader.load()
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=512, chunk_overlap=200)
    splits = text_splitter.split_documents(docs)
    # 获取文档和嵌入
    
    # documents, embeddings = get_siliconflow_embeddings(splits)
    siliconflow_embeddings = SiliconFlowEmbeddings(api_key="sk-cwonxmmcrmzdzpgmoomlagrhupjsyfrwfzhoipbcuvhaeplj")
    documents = [doc.page_content for doc in splits]
    embeddings = siliconflow_embeddings.embed_documents(documents)
    vectorstore = Chroma.from_documents(documents=splits, embedding=siliconflow_embeddings)

    
    print("文档加载并嵌入成功！！")
    return vectorstore

# 设置问答链
def setup_rag_chain(vectorstore, system_prompt, llm):
    retriever = vectorstore.as_retriever()

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            ("human", "{input}"),
        ]
    )
    question_answer_chain = create_stuff_documents_chain(llm, prompt)
    rag_chain = create_retrieval_chain(retriever, question_answer_chain)
    print("工作链设置成功！！")
    return rag_chain

#  提问和检索
def ask_question(question, file_path, promot, llm):
    # 加载并处理新文件
    vectorstore = load_and_process_pdf(file_path)
    
    # 重新设置问答链
    rag_chain = setup_rag_chain(vectorstore, promot, llm)
    
    # 提问并返回答案
    results = rag_chain.invoke({"input": question})
    print("问答成功！！")
    return results['answer']


def AI(question,retrieval_file, promot):
    base_url = "https://api.ppinfra.com/v3/openai"
    api_key = "sk_CZaTEK-dkQPo81US72zxQCp2ZTabPwpG_wSIx9b3HTE"
    model = "qwen/qwen3-8b-fp8"

    llm = ChatOpenAI(
        api_key = api_key,
        model=model,
        temperature=0.3,
        timeout=60,
        base_url=base_url,
    )
    # stream = True # or False
    # max_tokens = 1000
    
    # response_format = { "type": "text" }
 
    answer = ask_question(question, retrieval_file, promot, llm)
    print("Answer: ", answer)

    
class AICam:
    def __init__(self):
        
        # 工艺模板库
        self.data_process_template = pd.read_csv('data_gongyi.csv')

        # 工艺策略
        self.data_process_strategy = pd.read_csv('data_celue.csv')

        # 刀具库
        self.data_tool = pd.read_csv('data_daoju.csv')

    def AI_cam(self):
        pass

    def run(self):
        # 实现核心工艺流程
        selected_strategy = self.get_strategy()
        matched_template = self.get_template()
        optimal_tool = self.get_tool()
        
        
    
    # 选择策略
    def get_tool(self):
        pass
    def get_template(self):
        pass
    def get_strategy(self):
        pass

    # 设置策略
    def set_strategy(self):
        system_prompt = (
        """You are an assistant for question-answering tasks. 
        Use the following pieces of retrieved context to answer 
        the question. If you don't know the answer, say that you 
        don't know. Use three sentences maximum and keep the 
        answer concise."""
    )
        pass
    def set_template(self):
        system_prompt = (
        """You are an assistant for question-answering tasks. 
        Use the following pieces of retrieved context to answer 
        the question. If you don't know the answer, say that you 
        don't know. Use three sentences maximum and keep the 
        answer concise."""
    )
        pass
    def set_tool(self):
        system_prompt = (
        """You are an assistant for question-answering tasks. 
        Use the following pieces of retrieved context to answer 
        the question. If you don't know the answer, say that you 
        don't know. Use three sentences maximum and keep the 
        answer concise."""
    )
        pass

if __name__ == '__main__':
    AI("你好", "./diffdock.pdf", "你是一个人工智能助手  {context}")

    ai_cam = AICam()
    ai_cam.run()


