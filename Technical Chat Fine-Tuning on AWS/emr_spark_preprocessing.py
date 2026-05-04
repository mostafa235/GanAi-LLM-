# Imports
# Loads Apache Spark modules for DataFrame operations, text cleaning, window functions, and caching.
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, regexp_replace, trim, row_number
from pyspark.sql.window import Window
from pyspark import StorageLevel


# SETTINGS
# Defines input/output paths on S3 and lists all forums (datasets) to process.
S3_INPUT  = "s3://20596297-project-data/input/"
S3_OUTPUT = "s3://20596297-project-data/output/"

FORUMS = [
    "ai", "cs", "cstheory", "datascience",
    "askubuntu", "codegolf", "dba", "Stackoverflow"
]

# SPARK CONFIG (TUNED)
# Initializes Spark with performance tuning (memory, partitions, adaptive execution).
spark = SparkSession.builder \
    .appName("final-single-file-pipeline-full") \
    .config("spark.sql.adaptive.enabled", "true") \
    .config("spark.sql.shuffle.partitions", "600") \
    .config("spark.executor.memory", "6g") \
    .config("spark.driver.memory", "6g") \
    .getOrCreate()

spark.sparkContext.setLogLevel("ERROR")

print("\n" + "="*70)
print("PIPELINE STARTED (FORCING SINGLE FILE OUTPUT)")
print("="*70)

# CLEANING
# Removes URLs, HTML, code blocks, special characters, and extra spaces to normalize text.
def clean_text(c):
    c = regexp_replace(c, r"https?://\S+", "")
    c = regexp_replace(c, r"&lt;[^&gt;]+&gt;", "")
    c = regexp_replace(c, r"(?s)```.*?```", "")
    c = regexp_replace(c, r"[^\w\s.,!?]", " ")
    c = regexp_replace(c, r"\s+", " ")
    return trim(c)

# LOAD
# Reads each CSV, selects needed columns, casts types, removes nulls, cleans text, 
# and filters high-quality data (score ≥ 3).
def load_forum(name):
    path = f"{S3_INPUT}{name}.csv"
    print(f"\n Loading: {name}")

    df = spark.read \
        .option("header", "true") \
        .option("multiLine", "true") \
        .option("quote", '"') \
        .option("escape", '"') \
        .csv(path) \
        .select("question", "answer", "score")

    df = df.withColumn("score", col("score").cast("int")) \
           .dropna(subset=["question", "answer", "score"])

    df = df.withColumn("question", clean_text(col("question"))) \
           .withColumn("answer", clean_text(col("answer")))

    df = df.filter((col("question") != "") & (col("answer") != ""))
    df = df.filter(col("score") >= 3)

    print(f"  {name} ready")
    return df

# LOAD ALL DATA
# Applies the load function to all forums and stores them as DataFrames.
dfs = [load_forum(f) for f in FORUMS]

# UNION
# Merges all datasets into one unified DataFrame.
print("\n UNION...")
df = dfs[0]
for d in dfs[1:]:
    df = df.unionByName(d)

print(" UNION DONE")

# CACHE
# Stores data in memory/disk to speed up repeated operations.

print("\n Persisting dataset...")
df = df.persist(StorageLevel.MEMORY_AND_DISK)
df.count()
print(" Persisted")

# Deduplication
# Keeps only the highest-scoring answer per question using window ranking.
print("\n DEDUP...")

window = Window.partitionBy("question").orderBy(col("score").desc())

df = df.withColumn("rank", row_number().over(window)) \
       .filter(col("rank") == 1) \
       .drop("rank")

print(" DEDUP DONE")

# Final Selection
# Selects clean columns: question, answer, and score.
final_df = df.select("question", "answer", "score")

# Preview
# Displays a small sample of the processed data.
print("\n Preview:")
final_df.limit(5).show(truncate=80)

# SPLIT
# Splits data into training (80%), validation (10%), and test (10%).
train, val, test = final_df.randomSplit([0.8, 0.1, 0.1], seed=42)
print("\n Split done")

# SAVE SINGLE FILE FUNCTION
# Forces output into a single CSV file using repartition(1).
def save_single(df, name):
    path = f"{S3_OUTPUT}{name}/"
    print(f"\n Saving {name} as SINGLE FILE → {path}")

    df.repartition(1).write \
        .mode("overwrite") \
        .option("header", "true") \
        .csv(path)

    print(f" {name} saved as single file")

# SAVE
# Saves train, validation, test, and a small sample to S3.
save_single(train, "train")
save_single(val, "val")
save_single(test, "test")
save_single(final_df.limit(200), "sample")

# Stop Spark
# Shuts down the Spark session to release resources.
print("\n" + "="*70)
print(" PIPELINE COMPLETED (SINGLE FILE MODE)")
print("="*70)

spark.stop()