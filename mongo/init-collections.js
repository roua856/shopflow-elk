db = db.getSiblingDB("shopflow");
["users","files","searches","alert_rules","alerts"].forEach(c => { db[c].drop(); db.createCollection(c); });

db.users.createIndex({username:1},{unique:true});
db.users.createIndex({email:1},{unique:true});
db.files.createIndex({uploaded_at:-1}); db.files.createIndex({status:1}); db.files.createIndex({uploaded_by:1});
db.searches.createIndex({user_id:1, executed_at:-1});
db.alert_rules.createIndex({enabled:1}); db.alert_rules.createIndex({name:1});
db.alerts.createIndex({status:1, triggered_at:-1}); db.alerts.createIndex({rule_id:1});

const u = ObjectId("6650a0aa11bb22cc33dd44e1");
db.users.insertOne({_id:u, username:"roua", email:"roua@example.com", password_hash:"pbkdf2:sha256:600000$...", role:"analyst", is_active:true,
  created_at:ISODate("2026-10-23T09:00:00Z"), last_login:ISODate("2026-11-07T08:12:40Z"),
  settings:{page_size:50, default_levels:["ERROR","CRITICAL"], theme:"light"}});

db.files.insertOne({_id:ObjectId("6650a1f2c3d4e5f60718293a"), original_name:"orders_2026-10-20.csv",
  stored_name:"6650a1f2c3d4e5f60718293a__orders_2026-10-20.csv", format:"csv", size_bytes:4821337, uploaded_by:u,
  uploaded_at:ISODate("2026-10-20T14:07:02Z"), status:"indexed", logs_count:41250, error_count:12, error_message:null,
  ingestion:{started_at:ISODate("2026-10-20T14:07:05Z"), finished_at:ISODate("2026-10-20T14:07:19Z")}});

db.searches.insertOne({user_id:u, query_text:"timeout",
  filters:{levels:["ERROR","CRITICAL"], services:["payment-api"], date_from:ISODate("2026-10-20T00:00:00Z"), date_to:ISODate("2026-10-20T23:59:59Z")},
  results_count:318, duration_ms:142, executed_at:ISODate("2026-11-07T08:20:11Z")});

const r = ObjectId("6650a3c0c3d4e5f607182b10");
db.alert_rules.insertOne({_id:r, name:"Payment errors spike", description:"More than 20 ERROR or CRITICAL events from payment-api in 15 minutes",
  enabled:true, severity:"high",
  condition:{type:"threshold", window_minutes:15, operator:">", threshold:20,
    es_query:{bool:{filter:[{term:{service:"payment-api"}},{terms:{level:["ERROR","CRITICAL"]}}]}}},
  cooldown_minutes:30, channels:[{type:"email", target:"devops@example.com"}], created_by:u, created_at:ISODate("2026-11-02T10:00:00Z")});

db.alerts.insertOne({rule_id:r, rule_name:"Payment errors spike", severity:"high", status:"acknowledged",
  triggered_at:ISODate("2026-11-05T14:12:00Z"), observed_value:47, window_minutes:15, acknowledged_by:u,
  acknowledged_at:ISODate("2026-11-05T14:15:30Z"), resolved_at:null, snoozed_until:null,
  comments:[{user_id:u, text:"Payment gateway is down, provider contacted.", created_at:ISODate("2026-11-05T14:16:10Z")}],
  notifications:[{channel:"email", status:"sent", attempts:1, sent_at:ISODate("2026-11-05T14:12:03Z")}]});

print("Collections:", db.getCollectionNames());
