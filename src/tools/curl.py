from weaviate import Client

# 1) connect to your local Weaviate
client = Client("http://localhost:8080")

# 2) create the schema for the CarList class
client.schema.create_class({
    "class": "CarList",
    "properties": [
        {"name": "category", "dataType": ["text"]},
        # add other properties as needed
    ]
})

# 3) build the GraphQL aggregate query
graphql_agg = """
{
  Aggregate {
    CarList(groupBy:["category"]) {
      groupedBy {
        value
      }
      meta {
        count
      }
    }
  }
}
"""

# 4) send it as a raw GraphQL query
#    - v3 clients: client.query.raw(...)
#    - v4+ clients: client.graphql_raw_query(...)
# Here’s the v4+ form:
response = client.query.raw(graphql_agg)  # :contentReference[oaicite:0]{index=0}

# 5) walk the result and print each distinct category + count
groups = response["data"]["Aggregate"]["Carlist"]
for bucket in groups:
    cat = bucket["groupedBy"]["value"]
    cnt = bucket["meta"]["count"]
    print(f"{cat!r}: {cnt}")
