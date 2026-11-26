import os

tex_path = "PracticaNo4.tex"
with open(tex_path, "r", encoding="utf-8") as f:
    original = f.read()

# Find split points
pos_act = original.find(r"\seccion{ACTIVIDADES}")
pos_cuest = original.find(r"\seccion{CUESTIONARIO}")

header = original[:pos_act]
footer = original[pos_cuest:]

body = r"""\seccion{ACTIVIDADES}

Durante las sesiones de laboratorio se desarrolló de manera progresiva y experimental la práctica de almacenamiento no relacional y procesamiento masivo con \textit{MongoDB} y su integración con \textit{Python} mediante \textit{PyMongo} (MongoDB, Inc., s.~f.-d). A lo largo de la experiencia se exploró cómo los sistemas basados en documentos semiestructurados BSON facilitan la ingesta de grandes volúmenes de transacciones, la ejecución de agregaciones analíticas eficientes y la optimización de consultas mediante estructuras de indexación. Todo el proceso fue guiado por una metodología de contrastación empírica: en cada etapa se formuló primero una hipótesis analítica, luego se ejecutó la operación en consola o interfaz gráfica, y finalmente se verificaron los resultados contra cálculos independientes para certificar la integridad de los datos.

\vspace{0.2cm}
\noindent\textbf{1. Instalación y Configuración del Servidor MongoDB y mongosh (Actividades 1 y 2)}

En la fase inicial de la práctica se procedió con la instalación y configuración del entorno de base de datos no relacional sobre el sistema operativo Windows en arquitectura x86\_64. Se descargó y extrajo el paquete oficial de binarios de \textit{MongoDB Community Server 8.0.4}, organizando los ejecutables en la ruta estructurada \texttt{.\textbackslash mongodb\_dist\textbackslash mongodb-win32-x86\_64-windows-8.0.4\textbackslash bin\textbackslash}, la cual aloja el motor del servidor (\texttt{mongod.exe}) y el enrutador distribuido (\texttt{mongos.exe}) (MongoDB, Inc., s.~f.-a).

Paralelamente, se desplegó la consola interactiva oficial \textit{MongoDB Shell} (\texttt{mongosh} versión 2.3.8) dentro del directorio \texttt{.\textbackslash mongosh\_dist\textbackslash mongosh-2.3.8-win32-x64\textbackslash bin\textbackslash} (MongoDB, Inc., s.~f.-c). Con el propósito de establecer una configuración formal, persistente y reproducible, se elaboró el archivo de configuración \texttt{mongod.cfg}, en el cual se especificaron las directivas del servicio:
\begin{itemize}
    \item \textbf{Almacenamiento:} Ruta absoluta del directorio de datos (\texttt{storage.dbPath}) apuntando a \texttt{data\_db}, con el diario de transacciones habilitado (\texttt{journal.enabled: true}) para asegurar tolerancia ante fallas.
    \item \textbf{Registro del Sistema:} Destino en archivo (\texttt{systemLog.destination: file}) con registro continuo acumulativo (\texttt{logAppend: true}) en \texttt{mongod.log}.
    \item \textbf{Red y Conectividad:} Escucha en el puerto estándar \texttt{27017} con enlace restringido a la interfaz local segura \texttt{127.0.0.1} (\texttt{net.bindIp}).
\end{itemize}

Asimismo, se verificó la inicialización del directorio de almacenamiento \texttt{data\_db}, constatando la presencia de las tablas y metadatos del motor de almacenamiento transaccional \textit{WiredTiger} (\texttt{WiredTiger.wt}, ficheros de colecciones y registros de diagnóstico). Desde la consola de Windows PowerShell se ejecutó la comprobación de versión de los binarios (\texttt{mongod.exe --version} reportando v8.0.4 y \texttt{mongosh.exe --version} arrojando v2.3.8), como se documenta en la Figura 1:

\begin{center}
\begin{minipage}{0.84\textwidth}
\centering
\textbf{Figura 1} \\
\textit{Instalación de MongoDB Server 8.0, arquitectura del sistema, estructura de directorios y configuración formal en Windows (mongod.cfg)}
\vspace{4pt}

\includegraphics[width=\textwidth, height=9.2cm, keepaspectratio]{g4_a1_instalacion_mongodb.png}
\vspace{3pt}

\raggedright\footnotesize\textit{Nota}. Panel integral de instalación en Windows mostrando la verificación de versiones en PowerShell (\texttt{mongod} v8.0.4 y \texttt{mongosh} v2.3.8), el archivo de configuración oficial \texttt{mongod.cfg}, los binarios extraídos y la estructura del motor WiredTiger en \texttt{data\_db}.
\end{minipage}
\end{center}

\clearpage

A continuación, se procedió con la instalación de la herramienta cliente con interfaz gráfica de usuario: \textit{MongoDB Compass} versión 1.45.0 (MongoDB, Inc., s.~f.-b). Se descargó el paquete portable oficial de 64 bits y se extrajo en el directorio \texttt{.\textbackslash compass\_dist\textbackslash}. Al ejecutar la aplicación (\texttt{MongoDBCompass.exe}), se presentó la pantalla de bienvenida y el panel de configuración de conexión interactivo.

En dicho panel se configuró la cadena de conexión de acceso local \texttt{mongodb://localhost:27017} (apuntando al host \texttt{127.0.0.1} en el puerto \texttt{27017}), comprobando el estado receptivo de la interfaz visual antes de iniciar las operaciones documentales.

\begin{center}
\begin{minipage}{0.84\textwidth}
\centering
\textbf{Figura 2} \\
\textit{Instalación e interfaz gráfica de conexión inicial en MongoDB Compass conectándose a localhost:27017}
\vspace{4pt}

\includegraphics[width=\textwidth, height=9.2cm, keepaspectratio]{g4_a2_compass_instalacion_conexion.png}
\vspace{3pt}

\raggedright\footnotesize\textit{Nota}. Pantalla de bienvenida y diálogo de configuración de nueva conexión en la interfaz gráfica oficial de MongoDB Compass 1.45, estableciendo el enlace hacia la instancia local.
\end{minipage}
\end{center}

Seguidamente, se ejecutó el demonio del servidor \texttt{mongod} cargando la configuración establecida y se procedió a realizar la prueba de sondeo administrativo mediante la consola interactiva \texttt{mongosh}:
\begin{lstlisting}[language=bash]
mongosh "mongodb://localhost:27017" --eval "db.runCommand({ ping: 1 })"
\end{lstlisting}
El servidor respondió de inmediato con el documento BSON \texttt{\{ ok: 1 \}}, confirmando que el motor de base de datos se encontraba plenamente receptivo y en estado operativo para aceptar operaciones de lectura y escritura.

\begin{center}
\begin{minipage}{0.84\textwidth}
\centering
\textbf{Figura 3} \\
\textit{Arranque del motor WiredTiger y sondeo de conectividad con mongosh}
\vspace{4pt}

\includegraphics[width=\textwidth, height=9.2cm, keepaspectratio]{g4_a1_a2_servicio_ping.png}
\vspace{3pt}

\raggedright\footnotesize\textit{Nota}. Salida en consola de PowerShell mostrando la inicialización del motor WiredTiger en el puerto 27017 y la respuesta satisfactoria \texttt{\{ ok: 1 \}} del comando \texttt{ping}.
\end{minipage}
\end{center}

\clearpage

% ------------------------------------------------------------------------------
\noindent\textbf{2. Modelo Documental, CRUD y Primera Agregación (Actividades 3 y 4)}

Una vez comprobada la conexión, se seleccionó la base de datos de trabajo denominada \texttt{guia5\_bigdata}. Con el fin de comprender el comportamiento de los documentos sin la complejidad de grandes volúmenes, se crearon cuatro registros iniciales de ventas en la colección \texttt{ventas\_demo}.

Para garantizar que el lote pudiera ejecutarse repetidamente sin provocar duplicación accidental de documentos ni inconsistencias de clave primaria, se empleó la instrucción \texttt{replaceOne} acompañada del modificador \texttt{\{ upsert: true \}}, vinculando cada registro a un identificador estable (\texttt{G5-001} a \texttt{G5-004}). Este patrón de diseño asegura la \textit{idempotencia} de la carga: si el documento no existe en la colección, es insertado limpiamente; si ya existe, es reemplazado en su totalidad conservando el mismo identificador.

\begin{center}
\begin{minipage}{0.84\textwidth}
\centering
\textbf{Figura 4} \\
\textit{Carga y consulta de ventas iniciales en mongosh}
\vspace{4pt}

\includegraphics[width=\textwidth, height=9.2cm, keepaspectratio]{g4_a3_ventas_demo.png}
\vspace{3pt}

\raggedright\footnotesize\textit{Nota}. Ejecución del script \texttt{00\_ventas\_demo.js} mostrando la consulta de documentos de Arequipa, filtro por precio ($>500$) y ordenamiento descendente.
\end{minipage}
\end{center}

Tras ejecutar la carga en consola, se procedió a abrir la interfaz gráfica de \textit{MongoDB Compass}. Al conectarse a \texttt{localhost:27017}, la herramienta desplegó la vista general del cluster y la base de datos \texttt{guia5\_bigdata}, listando las colecciones activas junto con sus métricas operativas en tiempo real (tamaño de almacenamiento en disco, cantidad de documentos y recuento de índices), como se observa en la Figura 5:

\begin{center}
\begin{minipage}{0.84\textwidth}
\centering
\textbf{Figura 5} \\
\textit{Inspección visual de la base de datos guia5\_bigdata y resumen de colecciones en MongoDB Compass}
\vspace{4pt}

\includegraphics[width=\textwidth, height=9.2cm, keepaspectratio]{g4_compass_database_overview.png}
\vspace{3pt}

\raggedright\footnotesize\textit{Nota}. Vista de la base de datos \texttt{guia5\_bigdata} en MongoDB Compass, mostrando las tarjetas informativas de las colecciones \texttt{ventas\_masivas} (100K documentos), \texttt{sensores\_campus} (10K), \texttt{pruebas\_calidad} (6) y \texttt{ventas\_demo} (4).
\end{minipage}
\end{center}

\clearpage

Al ingresar a la colección \texttt{ventas\_demo} dentro de MongoDB Compass, la interfaz presentó la vista de documentos formateados interactivamente con tipado BSON diferenciado por color (cadenas en verde, valores numéricos en azul). Se comprobaron visualmente los cuatro registros de demostración (\texttt{G5-001} a \texttt{G5-004}), evidenciando que los datos persistidos en el motor son inmediatamente accesibles desde el entorno gráfico:

\begin{center}
\begin{minipage}{0.84\textwidth}
\centering
\textbf{Figura 6} \\
\textit{Navegación interactiva e inspección de documentos de la colección ventas\_demo en MongoDB Compass}
\vspace{4pt}

\includegraphics[width=\textwidth, height=9.2cm, keepaspectratio]{g4_compass_ventas_demo.png}
\vspace{3pt}

\raggedright\footnotesize\textit{Nota}. Visualización de los documentos de \texttt{ventas\_demo} en MongoDB Compass con sus campos tipados (\texttt{\_id}, \texttt{producto}, \texttt{ciudad}, \texttt{cantidad}, \texttt{precio}) y barra de consultas.
\end{minipage}
\end{center}

Posteriormente, en la Actividad 4, se completó el ciclo fundamental de manipulación de datos (CRUD) mediante la inserción de un registro temporal con identificador \texttt{G5-TEMP} (producto Prueba, Tacna, cantidad 1, precio 10). A continuación, se procedió a modificar su cantidad a 3 utilizando el operador atómico \texttt{\$set}, confirmándose la persistencia con \texttt{findOne}. Finalmente, se ejecutó \texttt{deleteOne(\{ \_id: "G5-TEMP" \})}, verificándose que el conteo de la colección retornó a los 4 documentos base.

Con los cuatro documentos limpios se ejecutó el primer pipeline de agregación analítica, agrupando por el campo \texttt{\$ciudad} y calculando los ingresos mediante la multiplicación acumulada de \texttt{cantidad} y \texttt{precio}:

\begin{center}
\begin{minipage}{0.84\textwidth}
\centering
\textbf{Figura 7} \\
\textit{Ciclo CRUD completo y cálculo de agregación por ciudad en mongosh}
\vspace{4pt}

\includegraphics[width=\textwidth, height=9.2cm, keepaspectratio]{g4_a4_crud_agregacion.png}
\vspace{3pt}

\raggedright\footnotesize\textit{Nota}. Salida de \texttt{00\_crud\_agregacion.js} mostrando inserción, actualización con \texttt{\$set}, eliminación puntual de \texttt{G5-TEMP} e ingresos agregados por ciudad.
\end{minipage}
\end{center}

La agregación consolidó $S/\,5\,200$ para Arequipa ($2 \times 2500 + 5 \times 40$) y $S/\,2\,800$ para Lima ($1 \times 2500 + 3 \times 100$), totalizando $S/\,8\,000$ entre ambas ciudades. Se comprobó de forma manual e independiente la exactitud de la operación.

\clearpage

% ------------------------------------------------------------------------------
\noindent\textbf{3. Integración con Python y PyMongo (Actividades 5 y 6)}

En la Actividad 5 se preparó el entorno de desarrollo en Python, creando un entorno virtual aislado con el módulo estándar \texttt{venv} (Python Software Foundation, s.~f.-b). A través del gestor de paquetes se instaló el controlador oficial \textit{PyMongo} (versión 4.19.0). 

En la Actividad 6 se implementó el script \texttt{01\_conexion.py}. El programa estableció comunicación con el servidor utilizando la clase \texttt{MongoClient}, fijó un tiempo límite de espera de conexión de 5000 milisegundos (\texttt{serverSelectionTimeoutMS}), envió una instrucción de sondeo administrativo y consultó los documentos de la colección \texttt{ventas\_demo}.

\begin{center}
\begin{minipage}{0.84\textwidth}
\centering
\textbf{Figura 8} \\
\textit{Conexión exitosa y consulta de documentos desde Python con PyMongo}
\vspace{4pt}

\includegraphics[width=\textwidth, height=9.2cm, keepaspectratio]{g4_a6_conexion_python.png}
\vspace{3pt}

\raggedright\footnotesize\textit{Nota}. Ejecución del script \texttt{01\_conexion.py} en PowerShell, demostrando la recuperación de documentos BSON como diccionarios nativos de Python.
\end{minipage}
\end{center}

Se comprendió que PyMongo traduce de forma transparente las estructuras documentales BSON a diccionarios y listas nativas de Python, permitiendo procesar información semiestructurada sin necesidad de mapeos objeto-relacionales (ORM) pesados.

\vspace{0.3cm}
\noindent\textbf{4. Ingesta Masiva por Lotes y Análisis con Validación Cruzada (Actividades 7 y 8)}

Para evaluar el desempeño de MongoDB bajo condiciones de mayor volumen, en la Actividad 7 se implementó el generador de transacciones sintéticas reproducibles \texttt{02\_generar\_datos.py}. Se configuró una población de $100\,000$ registros sobre una nueva colección denominada \texttt{ventas\_masivas}.

Con el objetivo de garantizar la total reproducibilidad matemática del experimento, se inicializó el generador pseudoaleatorio con una semilla fija (\texttt{random.Random(42)}). Cada registro incluyó una clave correlativa única \texttt{\_id}, una ciudad seleccionada entre cuatro urbes peruanas (Arequipa, Lima, Cusco y Tacna), un producto de catálogo con precio asociado, una cantidad entera entre 1 y 5 unidades, y una marca temporal UTC generada dentro de un horizonte de 100\,000 minutos a partir del 1 de enero de 2026.

La carga se estructuró en lotes de $1\,000$ documentos utilizando el método \texttt{insert\_many}, lo que minimizó drásticamente los viajes de ida y vuelta a la red (\textit{round-trips}) y optimizó las escrituras en el motor WiredTiger. El proceso completó la inserción de las $100\,000$ ventas en apenas 2.1 segundos, acumulando $300\,024$ unidades y un ingreso total generado de $S/\,251\,220\,720$.

\begin{center}
\begin{minipage}{0.84\textwidth}
\centering
\textbf{Figura 9} \\
\textit{Generación de 100\,000 registros por lotes y verificación de idempotencia}
\vspace{4pt}

\includegraphics[width=\textwidth, height=9.2cm, keepaspectratio]{g4_a7_generador_100k.png}
\vspace{3pt}

\raggedright\footnotesize\textit{Nota}. Salida de \texttt{02\_generar\_datos.py} mostrando el progreso por lotes de 1000 registros y la ejecución posterior demostrando el bloqueo de cargas accidentales.
\end{minipage}
\end{center}

\clearpage

Para verificar la persistencia y distribución de este gran volumen de datos, se abrió la colección \texttt{ventas\_masivas} en la interfaz gráfica de \textit{MongoDB Compass}. La herramienta constató la presencia de los \texttt{100.0K Documents} (almacenamiento de 2.81 MB), permitiendo explorar las transacciones con sus identificadores correlativos, fechas BSON e importes calculados, como se evidencia en la Figura 10:

\begin{center}
\begin{minipage}{0.84\textwidth}
\centering
\textbf{Figura 10} \\
\textit{Exploración de la colección masiva ventas\_masivas (100\,000 documentos) en la interfaz gráfica de MongoDB Compass}
\vspace{4pt}

\includegraphics[width=\textwidth, height=9.2cm, keepaspectratio]{g4_compass_ventas_masivas.png}
\vspace{3pt}

\raggedright\footnotesize\textit{Nota}. Vista de la colección \texttt{ventas\_masivas} en MongoDB Compass mostrando el conteo total de 100.0K documentos y la visualización de registros individuales con fechas BSON e importes.
\end{minipage}
\end{center}

En la Actividad 8 se implementó el script analítico \texttt{03\_analizar\_validar.py}. El objetivo consistió en responder a la pregunta de negocio: ¿cuántas transacciones, unidades e ingresos monetarios corresponden a cada ciudad? Para ello se utilizó un pipeline de agregación con las etapas \texttt{\$group} y \texttt{\$sort}:
\begin{lstlisting}[language=Python]
etapas = [
    {"$group": {
        "_id": "$ciudad",
        "ventas": {"$sum": 1},
        "unidades": {"$sum": "$cantidad"},
        "ingresos": {"$sum": {"$multiply": ["$cantidad", "$precio"]}}
    }},
    {"$sort": {"ingresos": -1, "_id": 1}}
]
\end{lstlisting}

En paralelo, para asegurar que el cálculo no dependiera ciegamente del motor de agregación, se programó en Python una rutina de validación independiente que recorrió los $100\,000$ documentos mediante un cursor por lotes (\texttt{batch\_size(1000)}), acumulando ventas, unidades e ingresos en un diccionario en memoria (\texttt{defaultdict}). Al contrastar ambas estructuras de datos, se certificó una coincidencia unívoca y exacta del 100\% entre ambos métodos.

\begin{center}
\begin{minipage}{0.84\textwidth}
\centering
\textbf{Figura 11} \\
\textit{Agregación analítica por ciudad y validación independiente en Python}
\vspace{4pt}

\includegraphics[width=\textwidth, height=9.2cm, keepaspectratio]{g4_a8_analizar_validar.png}
\vspace{3pt}

\raggedright\footnotesize\textit{Nota}. Resultados del script \texttt{03\_analizar\_validar.py} certificando la coincidencia exacta de los $100\,000$ registros entre el pipeline de MongoDB y el cómputo independiente.
\end{minipage}
\end{center}

\clearpage

Asimismo, la construcción de este pipeline analítico se examinó visualmente dentro de la pestaña \textit{Aggregations} de MongoDB Compass. La herramienta gráfica permite previsualizar interactivamente la estructura de los documentos en la colección y diseñar las fases de filtrado y agrupamiento mediante una interfaz intuitiva con vista previa de resultados en tiempo real, como se ilustra en la Figura 12:

\begin{center}
\begin{minipage}{0.84\textwidth}
\centering
\textbf{Figura 12} \\
\textit{Constructor visual de pipelines de agregación (Aggregation Builder) en MongoDB Compass}
\vspace{4pt}

\includegraphics[width=\textwidth, height=9.2cm, keepaspectratio]{g4_compass_aggregations.png}
\vspace{3pt}

\raggedright\footnotesize\textit{Nota}. Pestaña \textit{Aggregations} en MongoDB Compass mostrando la previsualización de documentos de la colección y el panel interactivo para la adición de etapas del pipeline.
\end{minipage}
\end{center}

\vspace{0.3cm}
\noindent\textbf{5. Evaluación de Índices y Exportación Analítica (Actividades 9 y 10)}

En la Actividad 9 se abordó el estudio del rendimiento de las consultas y la estructura de los planes de ejecución mediante el comando \texttt{explain("executionStats")} (MongoDB, Inc., s.~f.-f). Se formuló una consulta por rango temporal para recuperar todas las ventas correspondientes al día 10 de enero de 2026:
\begin{lstlisting}[language=Python]
filtro = {
    "fecha": {
        "$gte": datetime(2026, 1, 10, tzinfo=timezone.utc),
        "$lt": datetime(2026, 1, 11, tzinfo=timezone.utc)
    }
}
\end{lstlisting}

Se evaluó la consulta antes y después de crear un índice ascendente sobre el campo temporal (\texttt{db.ventas\_masivas.createIndex(\{ fecha: 1 \})}). Los resultados evidenciaron una transformación estructural profunda en la estrategia de búsqueda del optimizador:

\begin{center}
\begin{minipage}{0.84\textwidth}
\centering
\textbf{Figura 13} \\
\textit{Comparación del plan de ejecución antes y después de la creación del índice}
\vspace{4pt}

\includegraphics[width=\textwidth, height=9.2cm, keepaspectratio]{g4_a9_explain_indice.png}
\vspace{3pt}

\raggedright\footnotesize\textit{Nota}. Salida comparativa de \texttt{04\_explicar\_consulta.py} demostrando la transición de un escaneo de colección completa (COLLSCAN) a un escaneo de índice acotado (IXSCAN).
\end{minipage}
\end{center}

\clearpage

\begin{center}
\small
\noindent\textbf{Tabla 1} \\
\textit{Métricas comparativas del plan de ejecución antes y después de la indexación}
\vspace{4pt}

\begin{tabular}{lccc}
    \toprule
    \textbf{Métrica de Ejecución} & \textbf{Sin Índice (COLLSCAN)} & \textbf{Con Índice (IXSCAN + FETCH)} & \textbf{Variación / Mejora} \\
    \midrule
    Documentos retornados (\texttt{nReturned}) & 1\,424 & 1\,424 & Idéntico (100\%) \\
    Documentos examinados (\texttt{totalDocsExamined}) & 100\,000 & 1\,424 & Reducción del 98.6\% \\
    Claves examinadas (\texttt{totalKeysExamined}) & 0 & 1\,424 & Búsqueda puntual en árbol B \\
    Tiempo de ejecución (\texttt{executionTimeMillis}) & 31--39 ms & 3--6 ms & Reducción de $\approx 85\%$ \\
    \bottomrule
\end{tabular}
\vspace{3pt}

\raggedright\footnotesize\textit{Nota}. Datos obtenidos sobre la colección \texttt{ventas\_masivas} en MongoDB 8.0.4. Elaboración propia.
\end{center}

En MongoDB Compass, se accedió a la pestaña \textit{Indexes} de la colección \texttt{ventas\_masivas}. La interfaz gráfica evidenció de manera clara la existencia de los dos índices activos: la clave primaria única \texttt{\_id\_} (1.1 MB) y el índice secundario ascendente \texttt{fecha\_1} (1.1 MB), ambos en estado \texttt{READY}:

\begin{center}
\begin{minipage}{0.84\textwidth}
\centering
\textbf{Figura 14} \\
\textit{Gestión visual de índices en MongoDB Compass mostrando los índices \_id\_ y fecha\_1}
\vspace{4pt}

\includegraphics[width=\textwidth, height=9.2cm, keepaspectratio]{g4_compass_indexes.png}
\vspace{3pt}

\raggedright\footnotesize\textit{Nota}. Pestaña \textit{Indexes} en MongoDB Compass mostrando los dos índices creados sobre \texttt{ventas\_masivas}, su tamaño en disco (1.1 MB cada uno), propiedades y estado activo.
\end{minipage}
\end{center}

Seguidamente, se ejecutó la herramienta gráfica de diagnóstico \textit{Explain Plan} en MongoDB Compass. La interfaz generó el árbol visual interactivo (\textit{Visual Tree}), destacando de forma gráfica el nodo de escaneo de colección (\texttt{COLLSCAN}), con los 100\,000 documentos retornados y examinados en un tiempo de 20 ms:

\begin{center}
\begin{minipage}{0.84\textwidth}
\centering
\textbf{Figura 15} \\
\textit{Diagnóstico gráfico del plan de ejecución (Visual Tree COLLSCAN) en MongoDB Compass}
\vspace{4pt}

\includegraphics[width=\textwidth, height=9.2cm, keepaspectratio]{g4_compass_explain_plan.png}
\vspace{3pt}

\raggedright\footnotesize\textit{Nota}. Visualización del árbol del plan de ejecución en MongoDB Compass, evidenciando el costo del escaneo total (\texttt{COLLSCAN}) con 100\,000 documentos examinados y la alerta de rendimiento correspondiente.
\end{minipage}
\end{center}

\clearpage

Finalmente, en la Actividad 10 se ejecutó el script \texttt{05\_exportar\_csv.py}, el cual generó el archivo \texttt{resumen\_ciudades.csv} con codificación UTF-8 con BOM (\texttt{utf-8-sig}) (Python Software Foundation, s.~f.-a). El archivo contuvo exactamente la cabecera y cuatro filas consolidadas, verificándose su apertura y correspondencia plena con las cifras de la Actividad 8.

\begin{center}
\begin{minipage}{0.84\textwidth}
\centering
\textbf{Figura 16} \\
\textit{Generación y verificación del archivo CSV con el resumen de métricas}
\vspace{4pt}

\includegraphics[width=\textwidth, height=9.2cm, keepaspectratio]{g4_a10_exportar_csv.png}
\vspace{3pt}

\raggedright\footnotesize\textit{Nota}. Ejecución de \texttt{05\_exportar\_csv.py} y comprobación del contenido tabular de \texttt{resumen\_ciudades.csv}.
\end{minipage}
\end{center}

\clearpage

% ------------------------------------------------------------------------------
\seccion{EJERCICIOS}

En esta sección se desarrolla y narra la resolución de los cinco ejercicios planteados en la guía de laboratorio, documentando los comandos implementados, las salidas observadas y las pruebas de validación cruzada.

\vspace{0.2cm}
\noindent\textbf{1. Ejercicio 1: Consultas sobre las Cuatro Ventas Originales}

Sobre la colección \texttt{ventas\_demo} se ejecutaron cuatro consultas sin alterar el contenido de los registros base:

\begin{enumerate}[label=\alph*)]
    \item \textbf{Ventas de producto Laptop:} Se ejecutó \texttt{db.ventas\_demo.find(\{ producto: "Laptop" \})}, obteniéndose 2 documentos (\texttt{G5-001} en Arequipa y \texttt{G5-003} en Lima).
    \item \textbf{Ventas con cantidad mayor o igual a 3:} Se aplicó el filtro con operador de comparación \texttt{db.ventas\_demo.find(\{ cantidad: \{ \$gte: 3 \} \})}, recuperando los documentos \texttt{G5-002} (Mouse, 5 unidades) y \texttt{G5-004} (Teclado, 3 unidades).
    \item \textbf{Proyección de producto y cantidad sin identificador:} Se ejecutó \texttt{db.ventas\_demo.find(\{\}, \{ \_id: 0, producto: 1, cantidad: 1 \})}, excluyendo el campo \texttt{\_id} y mostrando únicamente las características solicitadas.
    \item \textbf{Cálculo de unidades acumuladas por ciudad:} Se diseñó un pipeline de agregación agrupando por ciudad y sumando el campo \texttt{cantidad}. Se determinó que Arequipa acumuló 7 unidades ($2 + 5$) y Lima 4 unidades ($1 + 3$), alcanzando un total de 11 unidades y certificando la exactitud del cálculo.
\end{enumerate}

\vspace{0.2cm}
\noindent\textbf{2. Ejercicio 2: Agregación por Producto sobre Ventas Masivas}

Se ejecutó un pipeline analítico sobre los $100\,000$ documentos de \texttt{ventas\_masivas}, agrupando por \texttt{\$producto} y ordenando por ingresos descendentes. Los resultados consolidados se presentan en la Tabla 2:

\begin{center}
\small
\noindent\textbf{Tabla 2} \\
\textit{Consolidación analítica de ventas, unidades e ingresos monetarios por producto}
\vspace{4pt}

\begin{tabular}{lcccc}
    \toprule
    \textbf{Producto} & \textbf{Ventas Realizadas} & \textbf{Unidades Vendidas} & \textbf{Ingresos Totales (S/)} & \textbf{Participación (\%)} \\
    \midrule
    Laptop & 25\,091 & 75\,455 & 188\,637\,500 & 75.09\% \\
    Monitor & 24\,888 & 74\,348 & 52\,043\,600 & 20.72\% \\
    Teclado & 25\,123 & 75\,513 & 7\,551\,300 & 3.00\% \\
    Mouse & 24\,898 & 74\,708 & 2\,988\,320 & 1.19\% \\
    \midrule
    \textbf{Total} & \textbf{100\,000} & \textbf{300\,024} & \textbf{251\,220\,720} & \textbf{100.00\%} \\
    \bottomrule
\end{tabular}
\vspace{3pt}

\raggedright\footnotesize\textit{Nota}. La suma de ingresos por producto ($S/\,251\,220\,720$) concuerda exactamente con la suma por ciudades obtenida en la Actividad 8. Elaboración propia.
\end{center}

\noindent\textit{Análisis conceptual:} Se observó que el producto con mayor número de transacciones y unidades comercializadas fue el \textit{Teclado} (25\,123 ventas y 75\,513 unidades), superando ligeramente a la \textit{Laptop} (25\,091 ventas). Sin embargo, la Laptop concentró más del 75\% del valor monetario global ($S/\,188\,637\,500$) debido a su precio unitario de $S/\,2\,500$, mientras que el Teclado tiene un precio de $S/\,100$. Esto evidenció que en el análisis de Big Data la métrica de frecuencia operativa no necesariamente guarda una relación directa con la métrica de impacto económico.

\vspace{0.3cm}
\noindent\textbf{3. Ejercicio 3: Filtrado Previo (\$match) antes de Agrupar (\$group)}

Se construyó un pipeline agregando primero una etapa de filtrado para Arequipa y luego agrupando por producto. El resultado arrojó un ingreso de $S/\,63\,777\,500$, idéntico al monto obtenido para Arequipa en la Actividad 8.

\noindent\textit{Reflexión técnica:} Se comprendió que la posición de la etapa \texttt{\$match} en el pipeline resulta determinante. Si se filtra antes de agrupar, MongoDB descarta tempranamente el 74.7\% de los documentos de la colección, procesando únicamente los $25\,293$ registros de Arequipa en la etapa \texttt{\$group}. En contraste, si se intentase agrupar primero por producto y filtrar después por ciudad, la consulta fallaría o requeriría incluir la ciudad en la clave de agrupación, debido a que el operador \texttt{\$group} proyecta únicamente los campos especificados en su definición y descarta los demás campos del documento original.

\clearpage

\begin{center}
\begin{minipage}{0.84\textwidth}
\centering
\textbf{Figura 17} \\
\textit{Ejecución de los Ejercicios 1, 2 y 3 sobre la base de datos de MongoDB}
\vspace{4pt}

\includegraphics[width=\textwidth, height=9.2cm, keepaspectratio]{g4_ejercicios_1_2_3.png}
\vspace{3pt}

\raggedright\footnotesize\textit{Nota}. Captura de PowerShell ejecutando el script \texttt{ejecutar\_ejercicios.py}, evidenciando las consultas puntuales, la agregación por producto y el filtrado por Arequipa.
\end{minipage}
\end{center}

\vspace{0.3cm}
\noindent\textbf{4. Ejercicio 4: Evaluación de Calidad de Datos y Saneamiento}

Se evaluó el conjunto de diez registros ficticios provisto en \texttt{pruebas\_calidad.json} sobre una colección separada denominada \texttt{pruebas\_calidad}. Se programó en Python una función de validación estricta sustentada en tres reglas de calidad:

\begin{enumerate}
    \item \textbf{Regla de Cantidad:} \texttt{type(cantidad) is int and cantidad > 0}. El uso de \texttt{type() is int} es mandatorio para descartar booleanos (\texttt{True} es subclase de entero en Python y evaluaría positivamente con \texttt{isinstance}).
    \item \textbf{Regla de Precio:} \texttt{type(precio) is int and precio > 0}. Permite rechazar cadenas de texto o valores monetarios no numéricos.
    \item \textbf{Regla de Ciudad:} \texttt{isinstance(ciudad, str) and bool(ciudad.strip())}. Asegura que el nombre de la ciudad no sea nulo ni esté conformado únicamente por espacios en blanco.
\end{enumerate}

De los 10 registros evaluados, 6 cumplieron cabalmente las reglas y fueron insertados en MongoDB mediante \texttt{replace\_one} con \texttt{upsert=True}, mientras que 4 registros fueron rechazados y catalogados con su causa de falla, como se detalla en la Tabla 3:

\begin{center}
\small
\noindent\textbf{Tabla 3} \\
\textit{Resultados de la auditoría de calidad de datos en pruebas\_calidad}
\vspace{4pt}

\begin{tabular}{cccll}
    \toprule
    \textbf{Identificador (\_id)} & \textbf{Cantidad} & \textbf{Precio} & \textbf{Ciudad} & \textbf{Dictamen y Causa de Rechazo} \\
    \midrule
    Q-001 al Q-006 & $1$ a $6$ & 40 & Arequipa & \textbf{Admitido:} Registro íntegro y válido \\
    Q-007 & $-2$ & 40 & Arequipa & \textbf{Rechazado:} Cantidad negativa fuera de rango \\
    Q-008 & 8 & "40" & Arequipa & \textbf{Rechazado:} Precio almacenado como texto \\
    Q-009 & 9 & 40 & "" & \textbf{Rechazado:} Campo de ciudad vacío \\
    Q-010 & \texttt{True} & 40 & Arequipa & \textbf{Rechazado:} Cantidad booleana no admisible \\
    \bottomrule
\end{tabular}
\vspace{3pt}

\raggedright\footnotesize\textit{Nota}. Total registros evaluados: 10 (6 válidos cargados en MongoDB y 4 rechazados). Elaboración propia.
\end{center}

\begin{center}
\begin{minipage}{0.84\textwidth}
\centering
\textbf{Figura 18} \\
\textit{Auditoría de calidad y filtrado de anomalías en el Ejercicio 4}
\vspace{4pt}

\includegraphics[width=\textwidth, height=9.2cm, keepaspectratio]{g4_ejercicio4_calidad.png}
\vspace{3pt}

\raggedright\footnotesize\textit{Nota}. Salida de \texttt{ejercicio4\_calidad.py} demostrando la identificación de anomalías y la inserción exclusiva de los documentos limpios en \texttt{pruebas\_calidad}.
\end{minipage}
\end{center}

\clearpage

Para certificar la correcta gobernanza de los datos en la base de datos, se abrió la colección \texttt{pruebas\_calidad} en la interfaz gráfica de \textit{MongoDB Compass}. La herramienta constató la presencia de exactamente los 6 documentos íntegros admitidos (\texttt{Q-001} a \texttt{Q-006}), confirmando que los cuatro registros defectuosos fueron descartados antes de impactar el almacenamiento persistente:

\begin{center}
\begin{minipage}{0.84\textwidth}
\centering
\textbf{Figura 19} \\
\textit{Inspección visual de la colección pruebas\_calidad en MongoDB Compass con los registros limpios admitidos}
\vspace{4pt}

\includegraphics[width=\textwidth, height=9.2cm, keepaspectratio]{g4_compass_pruebas_calidad.png}
\vspace{3pt}

\raggedright\footnotesize\textit{Nota}. Vista de la colección \texttt{pruebas\_calidad} en MongoDB Compass mostrando los 6 documentos válidos persistidos con sus identificadores \texttt{Q-001} a \texttt{Q-006} tras el proceso de saneamiento.
\end{minipage}
\end{center}

\vspace{0.3cm}
\noindent\textbf{5. Ejercicio 5: Caso de Estudio Original del Equipo}

Para aplicar las competencias adquiridas a un contexto no sensible del entorno universitario, se diseñó el sistema de \textbf{Monitoreo de Sensores Ambientales y Calidad del Aire en Aulas de la UCSM (EPIS - Smart Campus)}.

\begin{itemize}
    \item \textbf{Colección:} \texttt{sensores\_campus} dentro de la base de datos \texttt{guia5\_bigdata}.
    \item \textbf{Esquema Documental:} Cada lectura de sensor quedó estructurada mediante seis campos:
    \begin{align*}
        \{ &\text{\_id}: \text{int (correlativo 1 a 10\,000)}, \\
           &\text{sensor\_id}: \text{string ("SNS-SIS3", "SNS-A101", etc.)}, \\
           &\text{aula}: \text{string ("Lab-Sistemas", "Pabellon-A", "Pabellon-B", "Auditorio")}, \\
           &\text{co2\_ppm}: \text{int (concentración de CO}_2\text{ entre 400 y 1800 ppm)}, \\
           &\text{temperatura\_c}: \text{float (temperatura en grados Celsius entre 18.0 y 28.5 }^\circ\text{C)}, \\
           &\text{timestamp}: \text{datetime (marca temporal UTC durante el mes de marzo de 2026)} \}
    \end{align*}
    \item \textbf{Generación y Carga por Lotes:} Se fijó la semilla pseudoaleatoria \texttt{random.Random(100)} y se generaron $10\,000$ documentos distribuidos en lotes de $500$ registros (\texttt{insert\_many}). El código verificó que si la colección ya contaba con datos, abortaba la carga para evitar duplicaciones.
    \item \textbf{Consultas y Filtros Analíticos:}
    \begin{itemize}
        \item \textit{Filtro 1 (Alertas de Ventilación):} Se evaluó \texttt{\{"co2\_ppm": \{"\$gt": 1200\}\}}, detectándose $4\,260$ lecturas con niveles de dióxido de carbono por encima del umbral de confort ambiental.
        \item \textit{Filtro 2 (Inspección Temporal en Laboratorio):} Se consultaron las lecturas del ambiente \texttt{Lab-Sistemas} durante las primeras 24 horas (\texttt{2026-03-01}), recuperándose exactamente $98$ registros.
    \end{itemize}
    \item \textbf{Pipeline de Agregación:} Se agruparon las lecturas por aula calculando lecturas totales, media de $\text{CO}_2$, media de temperatura y total de alertas, como se resume en la Tabla 4:
\end{itemize}

\clearpage

\begin{center}
\small
\noindent\textbf{Tabla 4} \\
\textit{Métricas ambientales y alertas de calidad de aire consolidadas por ambiente}
\vspace{4pt}

\begin{tabular}{lcccc}
    \toprule
    \textbf{Ambiente del Campus} & \textbf{Lecturas Totales} & \textbf{$\text{CO}_2$ Medio (ppm)} & \textbf{Temp. Media ($^\circ$C)} & \textbf{Lecturas Críticas ($>1200$)} \\
    \midrule
    Auditorio & 2\,518 & 1\,093.66 & 23.26 & 1\,028 \\
    Lab-Sistemas & 2\,533 & 1\,100.01 & 23.25 & 1\,095 \\
    Pabellon-A & 2\,516 & 1\,106.04 & 23.20 & 1\,091 \\
    Pabellon-B & 2\,433 & 1\,102.25 & 23.30 & 1\,046 \\
    \midrule
    \textbf{Total Consolidado} & \textbf{10\,000} & \textbf{1\,100.49} & \textbf{23.25} & \textbf{4\,260} \\
    \bottomrule
\end{tabular}
\vspace{3pt}

\raggedright\footnotesize\textit{Nota}. Resultados validados mediante cálculo independiente secuencial en Python con 100\% de concordancia. Elaboración propia.
\end{center}

\begin{itemize}
    \item \textbf{Propuesta de Índice Compuesto y Justificación:}
    Para acelerar las consultas frecuentes que buscan eventos en un aula específica dentro de ventanas de tiempo acotadas, se propuso el índice compuesto \texttt{\{ aula: 1, timestamp: 1 \}}.
    Al ejecutar la prueba de rendimiento mediante \texttt{explain("executionStats")}, la búsqueda sin índice requirió examinar los $10\,000$ documentos de la colección (\texttt{COLLSCAN}). Con el índice compuesto, el motor utilizó un plan \texttt{IXSCAN + FETCH}, examinando únicamente las $98$ claves y los $98$ documentos pertenecientes al día consultado, alcanzando una optimización del $99.0\%$ en documentos examinados.
    \item \textbf{Recuperación y Control de Interrupciones:}
    Se documentó que, en caso de interrupción durante la carga masiva, la presencia de identificadores correlativos fijos permite consultar el último \texttt{\_id} persistido exitosamente y reanudar la carga desde ese punto sin alterar datos previos ni requerir borrados destructivos de colecciones.
\end{itemize}

\begin{center}
\begin{minipage}{0.84\textwidth}
\centering
\textbf{Figura 20} \\
\textit{Ejecución completa del caso de estudio de sensores y validación de índice compuesto}
\vspace{4pt}

\includegraphics[width=\textwidth, height=9.2cm, keepaspectratio]{g4_ejercicio5_sensores.png}
\vspace{3pt}

\raggedright\footnotesize\textit{Nota}. Salida de \texttt{ejercicio5\_caso\_equipo.py} evidenciando la generación de lecturas, el análisis por ambientes, la validación independiente y la optimización con índice compuesto.
\end{minipage}
\end{center}

\clearpage

Asimismo, la colección \texttt{sensores\_campus} fue inspeccionada en la interfaz gráfica de \textit{MongoDB Compass}. Se visualizaron los documentos individuales con sus métricas ambientales registradas (valores de dióxido de carbono, temperatura y marcas temporales UTC):

\begin{center}
\begin{minipage}{0.84\textwidth}
\centering
\textbf{Figura 21} \\
\textit{Exploración de lecturas IoT de la colección sensores\_campus en MongoDB Compass}
\vspace{4pt}

\includegraphics[width=\textwidth, height=9.2cm, keepaspectratio]{g4_compass_sensores_campus.png}
\vspace{3pt}

\raggedright\footnotesize\textit{Nota}. Vista de documentos de la colección \texttt{sensores\_campus} en MongoDB Compass mostrando las lecturas ambientales de los diferentes pabellones del campus universitario.
\end{minipage}
\end{center}

Finalmente, se comprobó en la pestaña \textit{Indexes} de MongoDB Compass la presencia del índice compuesto propuesto (\texttt{aula\_1\_timestamp\_1}). La herramienta gráfica constató que dicho índice ocupa 131.1 KB en disco, está tipado como compuesto (\texttt{COMPOUND}) y se encuentra en estado plenamente operativo (\texttt{READY}):

\begin{center}
\begin{minipage}{0.84\textwidth}
\centering
\textbf{Figura 22} \\
\textit{Detalle del índice compuesto aula\_1\_timestamp\_1 en MongoDB Compass}
\vspace{4pt}

\includegraphics[width=\textwidth, height=9.2cm, keepaspectratio]{g4_compass_sensores_indexes.png}
\vspace{3pt}

\raggedright\footnotesize\textit{Nota}. Pestaña \textit{Indexes} de \texttt{sensores\_campus} en MongoDB Compass mostrando el índice compuesto \texttt{aula\_1\_timestamp\_1} (131.1 KB) activo junto a la clave primaria.
\end{minipage}
\end{center}

\clearpage

% ------------------------------------------------------------------------------
\noindent\textbf{6. Ampliación Opcional: Cálculo de Promedios Ponderados y la Falacia del Promedio de Promedios}

Durante el análisis cuantitativo de las agrupaciones, se examinó con especial rigor metodológico el cálculo del precio promedio y el ingreso promedio por transacción. Un error analítico frecuente en la minería de Big Data consiste en calcular primero el promedio de cada grupo (por ejemplo, el promedio de ventas por ciudad) y luego promediar aritméticamente dichos promedios:
\begin{equation}
    \bar{x}_{\text{ingenuo}} = \frac{1}{k} \sum_{j=1}^{k} \bar{x}_j
\end{equation}

Al evaluar las cuatro ciudades de nuestra población de $100\,000$ registros:
\begin{itemize}
    \item Arequipa: $S/\,63\,777\,500 / 25\,293 = S/\,2\,521.55$ por venta.
    \item Cusco: $S/\,62\,677\,400 / 25\,038 = S/\,2\,503.29$ por venta.
    \item Lima: $S/\,62\,417\,440 / 24\,776 = S/\,2\,519.27$ por venta.
    \item Tacna: $S/\,62\,348\,380 / 24\,893 = S/\,2\,504.66$ por venta.
\end{itemize}

El promedio aritmético simple de estos cuatro valores arroja:
\begin{equation}
    \bar{x}_{\text{ingenuo}} = \frac{2521.55 + 2503.29 + 2519.27 + 2504.66}{4} = S/\,2\,512.19
\end{equation}

Sin embargo, el promedio ponderado real de la población completa de $100\,000$ ventas es:
\begin{equation}
    \bar{x}_{\text{real}} = \frac{\sum_{j=1}^{k} \sum_{i=1}^{n_j} x_{ji}}{\sum_{j=1}^{k} n_j} = \frac{S/\,251\,220\,720}{100\,000} = S/\,2\,512.21
\end{equation}

Aunque en esta muestra grande la discrepancia parece pequeña ($0.02$ soles), en subgrupos con cardinalidades marcadamente asimétricas la distorsión puede ser catastrófica (como se demostró en la práctica de MapReduce con grupos de 100 y 2 elementos donde el error superó el 180\%). En MongoDB, la manera canónica y matemáticamente rigurosa de resolver promedios consiste en utilizar el acumulador \texttt{\$avg} o en transportar acumuladores aditivos de tupla $(\sum x_i, \sum n_i)$, asegurando que la división escalar se efectúe únicamente al final sobre los totales consolidados.

\clearpage

"""

new_tex = header + body + footer

with open(tex_path, "w", encoding="utf-8") as f:
    f.write(new_tex)

print("Updated PracticaNo4.tex successfully! New length:", len(new_tex))
