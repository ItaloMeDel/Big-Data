#!/usr/bin/env bash
# Uso:  ./run_hadoop.sh local   (MapReduce de Hadoop sobre archivos locales, sin demonios)
#       ./run_hadoop.sh hdfs    (entrada/salida en HDFS; requiere NameNode y DataNode activos, ver README)
# Nota: Hadoop falla con rutas con espacios ("Trabajo Integrador"), por eso se trabaja en un directorio temporal sin espacios.
set -euo pipefail
MODE="${1:-local}"
AQUI="$(cd "$(dirname "$0")" && pwd)"
RES="${RES_DIR:-$AQUI/../resultados}"
export HADOOP_HOME="${HADOOP_HOME:-$HOME/hadoop-3.3.6}"
export JAVA_HOME="${JAVA_HOME:-$(dirname "$(dirname "$(readlink -f "$(which java)")")")}"
export PATH="$HADOOP_HOME/bin:$PATH"
JAR="$(ls "$HADOOP_HOME"/share/hadoop/tools/lib/hadoop-streaming-*.jar | head -1)"
CSV="$RES/era5_obs.csv"
[ -f "$CSV" ] || { echo "Falta $CSV (ejecuta 05_exportar_para_hadoop.py)"; exit 1; }
TS="$(date +%Y%m%d-%H%M%S)"
W="/tmp/era5_mr_$TS"; mkdir -p "$W"
cp "$AQUI/mapper.py" "$AQUI/reducer.py" "$W/"
echo "Hadoop: $(hadoop version | head -1) | Java: $("$JAVA_HOME/bin/java" -version 2>&1 | head -1) | modo: $MODE"
if [ "$MODE" = "hdfs" ]; then
  hdfs dfs -mkdir -p /era5/entrada
  hdfs dfs -put -f "$CSV" /era5/entrada/
  hdfs dfs -ls -h /era5/entrada
  hdfs fsck /era5/entrada -files -blocks | tail -15
  OUT="/era5/salida-$TS"; IN="/era5/entrada/era5_obs.csv"
else
  cp "$CSV" "$W/era5_obs.csv"
  OUT="$W/salida"; IN="$W/era5_obs.csv"
fi
hadoop jar "$JAR" -files "$W/mapper.py,$W/reducer.py" \
  -input "$IN" -output "$OUT" -mapper "python3 mapper.py" -reducer "python3 reducer.py"
if [ "$MODE" = "hdfs" ]; then
  hdfs dfs -ls "$OUT"; hdfs dfs -cat "$OUT"/part-* | sort > "$RES/hadoop_resultado.tsv"
else
  ls "$OUT"; cat "$OUT"/part-* | sort > "$RES/hadoop_resultado.tsv"
fi
echo "Resultado en $RES/hadoop_resultado.tsv ($(wc -l < "$RES/hadoop_resultado.tsv") claves)"
