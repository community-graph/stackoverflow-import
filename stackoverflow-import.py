# pulling questions from this API endpoint: https://api.stackexchange.com/docs/questions

import os
import requests
from neo4j.v1 import GraphDatabase, basic_auth

neo4jUrl = os.environ.get('NEO4J_URL',"bolt://localhost")
neo4jUser = os.environ.get('NEO4J_USER',"neo4j")
neo4jPass = os.environ.get('NEO4J_PASSWORD',"test")
driver = GraphDatabase.driver(neo4jUrl, auth=basic_auth(neo4jUser, neo4jPass))

session = driver.session()

# Add uniqueness constraints.
session.run("CREATE CONSTRAINT ON (q:Question) ASSERT q.id IS UNIQUE;").consume()

page=1
items=100
tag="Neo4j"

# Build URL.
apiUrl = "https://api.stackexchange.com/2.2/questions?page={page}&pagesize={items}&order=asc&sort=creation&tagged={tag}&site=stackoverflow&filter=!5-i6Zw8Y)4W7vpy91PMYsKM-k9yzEsSC1_Uxlf".format(tag=tag,page=page,items=items)

result = session.run("MATCH (q:Question) RETURN max(q.creation_date) as max_date")

for record in result:
	apiUrl += "&min={maxDate}".format(maxDate=record["max_date"])

# Send GET request.
json = requests.get(apiUrl, headers = {"accept":"application/json"}).json()


# # test query.
# query = """
# WITH {json} as data
# UNWIND data.items as q
# WITH q, q.question_id as question, q.owner.user_id as owner, q.tags as tags
# UNWIND q.answers as a 
# RETURN question, owner,tags, a.answer_id as a_id, a.owner.user_id as a_owner_id
# """
# result = session.run(query,{"json":json})
# for record in result:
#     print(record)


# Build query.
query2 = """
WITH {json} as data
UNWIND data.items as q
MERGE (question:Question {id:q.question_id}) 
  ON CREATE SET question.title = q.title, question.share_link = q.share_link, question.creation_date = q.creation_date
SET question.favorite_count = q.favorite_count, question.last_activity_date = q.last_activity_date

FOREACH (q_owner IN [o in [q.owner] WHERE o.user_id IS NOT NULL] |
  MERGE (owner:User {id:q.owner.user_id}) ON CREATE SET owner.display_name = q.owner.display_name
  MERGE (owner)-[:ASKED]->(question)
)

FOREACH (tagName IN q.tags | MERGE (tag:Tag {name:tagName}) MERGE (question)-[:TAGGED]->(tag))
FOREACH (a IN q.answers |
   MERGE (question)<-[:ANSWERS]-(answer:Answer {id:a.answer_id})
   FOREACH (a_owner IN filter(o IN [a.owner] where o.user_id is not null) |
     MERGE (answerer:User {id:a_owner.user_id}) ON CREATE SET answerer.display_name = a_owner.display_name
     MERGE (answer)<-[:PROVIDED]-(answerer)
   )
)
"""

# Execute Query with Parameter
result = session.run(query2,{"json":json})

print(result.consume().counters)

session.close()

