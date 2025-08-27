class Glossary:
    def __init__(self,glossary_dict:dict[str:str]=None):
        self.glossary_dict=glossary_dict

    def update(self,update_dict:dict[str:str]):
        for src,dst in update_dict.items():
            if src not in self.glossary_dict:
                self.glossary_dict[src]=dst

    def append_system_prompt(self,text:str):
        prompt="\n以下为参考术语表:\n"
        for src,dst in self.glossary_dict.items():
            if src in text:
                prompt+=f"{src}=>{dst}\n"
        prompt+="术语表结束\n"
        return prompt
