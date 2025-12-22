import json
import logging
from src.logging_config import setup_logging
from src.Agent import Agent
# Setup logging
setup_logging(level=logging.INFO, log_file="logs/app.log")
logger = logging.getLogger(__name__)


file_d="diabetes.json"

###############################################
#       agent testing local
###############################################

# #create agent
# agent = Agent(
#         name="HealthAssistant",
#         model="ollama/deepseek-r1:14b",
#         api_key=None,
#         api_base="http://localhost:11434",
#         system_prompt="You are a helpful assistant specialized ."
#     )

# print("\n=== Agent Demo ===")
# response = agent.chat("Quelle heure est-il ?")
# print(f"Agent: {response}")

###############################################
#       generate question
###############################################
""" parsing_trials_answer is use to parse answer and prepare the format for the ingestion"""

def eligibilities_criteria_fetcher():
    """
    IOSITFOF: index of study in the files of studies
    """
    criterias_list=[]
    
    with open (file_d, "r", encoding="utf-8") as f:
        data=json.load(f)

    studies=data.get('studies')
    for i in range (0,len(studies)):
        study= studies[i].get("protocolSection")
        id_study=study.get("identificationModule").get("nctId")
        eligibilityCriteria_study=study.get("eligibilityModule").get("eligibilityCriteria")
        
        # print(f"index_in_studies_file::{i}\nid study :: {id_study}\neligibilty criteria::{eligibilityCriteria_study}")
        criterias_list.append(dict({'index_in_studies_file':i,
                                    'id_of_study(nctId)': id_study, 
                                    "criterias":eligibilityCriteria_study}
                            )
                        )
    return criterias_list

criterias=eligibilities_criteria_fetcher() 
print(f'criterias: {criterias[0]}')