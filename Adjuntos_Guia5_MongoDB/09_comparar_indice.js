// Ejecutar después de cargar ventas_masivas. No elimina índices existentes.
db = db.getSiblingDB("guia5_bigdata");
const ventas = db.getCollection("ventas_masivas");
if (!ventas.countDocuments({})) throw new Error("Primero ejecutar 02_generar_datos.py");
if (ventas.getIndexes().some(i => Object.prototype.hasOwnProperty.call(i.key, "fecha"))) {
 throw new Error("Ya hay un índice de fecha. Usar una colección nueva y adaptar los nombres.");
}
const filtro = {fecha: {$gte: ISODate("2026-01-10T00:00:00Z"), $lt: ISODate("2026-01-11T00:00:00Z")}};
print("ANTES");
printjson(ventas.find(filtro).explain("executionStats"));
print(ventas.createIndex({fecha: 1}));
print("DESPUÉS");
printjson(ventas.find(filtro).explain("executionStats"));
