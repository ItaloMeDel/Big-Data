db = db.getSiblingDB("guia5_bigdata");
if (db.ventas_demo.findOne({_id: "G5-TEMP"})) {
  throw new Error("G5-TEMP ya existe; revisar antes de insertar otra vez.");
}
printjson(db.ventas_demo.insertOne({_id: "G5-TEMP", producto: "Prueba", ciudad: "Tacna", cantidad: 1, precio: 10}));
printjson(db.ventas_demo.updateOne({_id: "G5-TEMP"}, {$set: {cantidad: 3}}));
printjson(db.ventas_demo.findOne({_id: "G5-TEMP"}));
printjson(db.ventas_demo.deleteOne({_id: "G5-TEMP"}));
print("Ventas restantes:", db.ventas_demo.countDocuments({}));
printjson(db.ventas_demo.aggregate([
 {$group: {_id: "$ciudad", ingresos: {$sum: {$multiply: ["$cantidad", "$precio"]}}, ventas: {$sum: 1}}},
 {$sort: {ingresos: -1}}
]).toArray());
