from docutranslate.ir.document import Document


class Glossary:
    def __init__(self,glossary_dict:dict[str:str]=None):
        self.glossary_dict=glossary_dict

    def update(self,update_dict:dict[str:str]):
        for src,dst in update_dict.items():
            if src not in self.glossary_dict:
                self.glossary_dict[src]=dst

    def append_system_prompt(self,text:str):
        flag=False
        prompt="\n以下为参考术语表:\n"
        for src,dst in self.glossary_dict.items():
            if src in text:
                prompt+=f"{src}=>{dst}\n"
                flag=True
        prompt+="术语表结束\n"
        if flag:
            return prompt
        else:
            return ""
    @staticmethod
    def glossary_dict2csv(glossary_dict: dict[str, str], seperator=",", stem="glossary_gen") -> Document:
        content = f"src{seperator}dst\n"
        for src, dst in glossary_dict.items():
            content += f"{src}{seperator}{dst}\n"
        return Document.from_bytes(content=content.encode("utf-8"), suffix=".csv", stem=stem)