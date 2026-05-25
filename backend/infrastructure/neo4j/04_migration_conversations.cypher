// Migrate legacy Client-[:HAS_MESSAGE]->ChatMessage to Conversation threads
MATCH (cl:Client)-[old:HAS_MESSAGE]->(m:ChatMessage)
WHERE NOT (m)<-[:HAS_MESSAGE]-(:Conversation)
WITH cl, collect(m) AS msgs, collect(old) AS rels
WHERE size(msgs) > 0
CREATE (conv:Conversation {
  id: randomUUID(),
  title: 'Legacy chat',
  created_at: coalesce(msgs[0].created_at, datetime()),
  updated_at: coalesce(msgs[size(msgs)-1].created_at, datetime())
})
CREATE (conv)-[:FOR_CLIENT]->(cl)
FOREACH (msg IN msgs | CREATE (conv)-[:HAS_MESSAGE]->(msg))
FOREACH (r IN rels | DELETE r);
