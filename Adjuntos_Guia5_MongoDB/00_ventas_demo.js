// PowerShell: mongosh "mongodb://localhost:27017" --file 00_ventas_demo.js
db = db.getSiblingDB("guia5_bigdata");
const iniciales = [
  {
    "_id": "G5-001",
    "producto": "Laptop",
    "ciudad": "Arequipa",
    "cantidad": 2,
    "precio": 2500
  },
  {
    "_id": "G5-002",
    "producto": "Mouse",
    "ciudad": "Arequipa",
    "cantidad": 5,
    "precio": 40
  },
  {
    "_id": "G5-003",
    "producto": "Laptop",
    "ciudad": "Lima",
    "cantidad": 1,
    "precio": 2500
  },
  {
    "_id": "G5-004",
    "producto": "Teclado",
    "ciudad": "Lima",
    "cantidad": 3,
    "precio": 100
  }
];
iniciales.forEach(venta => db.ventas_demo.replaceOne({_id: venta._id}, venta, {upsert: true}));
print("Total:", db.ventas_demo.countDocuments({}));
printjson(db.ventas_demo.find({ciudad: "Arequipa"}).toArray());
printjson(db.ventas_demo.find({precio: {$gt: 500}}).toArray());
printjson(db.ventas_demo.find({}, {_id: 0, producto: 1, ciudad: 1, precio: 1}).sort({precio: -1}).toArray());
