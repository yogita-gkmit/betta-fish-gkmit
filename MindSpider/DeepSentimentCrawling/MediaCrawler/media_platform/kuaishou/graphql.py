# Declaration: This code is for learning and research purposes only. Users must adhere to the following principles:  
# 1. Do not use for any commercial purposes.  
# 2. Comply with the target platform's terms of use and robots.txt rules.  
# 3. Do not perform large-scale crawling or disrupt platform operations.  
# 4. Reasonably control request frequency to avoid unnecessary burden on the target platform.   
# 5. Do not use for any illegal or improper purposes.
#   
# For detailed license terms, please refer to the LICENSE file in the project root directory.  
# Using this code indicates your agreement to abide by the above principles and all terms in the LICENSE.  


# Kuaishou data transmission is based on GraphQL implementation
# This class is responsible for obtaining some GraphQL schemas
from typing import Dict


class KuaiShouGraphQL:
    graphql_queries: Dict[str, str]= {}

    def __init__(self):
        self.graphql_dir = "media_platform/kuaishou/graphql/"
        self.load_graphql_queries()

    def load_graphql_queries(self):
        graphql_files = ["search_query.graphql", "video_detail.graphql", "comment_list.graphql", "vision_profile.graphql","vision_profile_photo_list.graphql","vision_profile_user_list.graphql","vision_sub_comment_list.graphql"]

        for file in graphql_files:
            with open(self.graphql_dir + file, mode="r") as f:
                query_name = file.split(".")[0]
                self.graphql_queries[query_name] = f.read()

    def get(self, query_name: str) -> str:
        return self.graphql_queries.get(query_name, "Query not found")
