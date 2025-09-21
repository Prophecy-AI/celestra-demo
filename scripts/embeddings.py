import pandas as pd
import numpy as np
from openai import OpenAI
import json
import os
from typing import List, Union
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def generate_embedding(text: Union[str, List[str]], model: str = "text-embedding-3-small") -> Union[List[float], List[List[float]]]:
    if isinstance(text, str):
        text = [text]
    
    # Filter out empty strings
    valid_texts = [t for t in text if t and t.strip()]
    if not valid_texts:
        return []
    
    response = client.embeddings.create(
        input=valid_texts,
        model=model
    )
    
    embeddings = [data.embedding for data in response.data]
    
    if len(text) == 1:
        return embeddings[0] if embeddings else []
    
    return embeddings

def compute_similarity(embedding1: List[float], embedding2: List[float]) -> float:

    if not embedding1 or not embedding2:
        return 0.0
    
    vec1 = np.array(embedding1)
    vec2 = np.array(embedding2)
    
    dot_product = np.dot(vec1, vec2)
    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)
    
    if norm1 == 0 or norm2 == 0:
        return 0.0
    
    return dot_product / (norm1 * norm2)

def embed_text_columns(df: pd.DataFrame, text_columns: List[str]) -> pd.DataFrame:
    df_copy = df.copy()
    
    for column in text_columns:
        if column not in df_copy.columns:
            print(f"Warning: Column '{column}' not found in dataframe")
            continue
        
        print(f"Generating embeddings for column: {column}")
        embedding_column = f"{column}_embedding"
        
        embeddings = []
        for idx, value in df_copy[column].items():
            if pd.isna(value) or value == '' or value == '[]':
                embeddings.append([])
                continue
            
            # Parse the value into a list
            if isinstance(value, list):
                items_list = value
            elif isinstance(value, str) and value.startswith('['):
                try:
                    parsed = json.loads(value)
                    if isinstance(parsed, list):
                        items_list = parsed
                    else:
                        items_list = [str(value)]
                except:
                    items_list = [str(value)]
            else:
                items_list = [str(value)]
            
            # Generate embeddings for each item individually
            try:
                if len(items_list) == 1:
                    # Single item - generate one embedding
                    embedding = generate_embedding(items_list[0])
                    embeddings.append(embedding)
                else:
                    # Multiple items - generate embedding for each and store as list of embeddings
                    item_embeddings = []
                    for item in items_list:
                        if item and str(item).strip():
                            item_embedding = generate_embedding(str(item).strip())
                            item_embeddings.append(item_embedding)
                    embeddings.append(item_embeddings)
                
                # Progress indicator
                if (idx + 1) % 10 == 0:
                    print(f"  Processed {idx + 1}/{len(df_copy)} rows")
                    
            except Exception as e:
                print(f"Error embedding row {idx}: {e}")
                embeddings.append([])
        
        df_copy[embedding_column] = embeddings
        print(f"  Completed {column} -> {embedding_column}")
    
    return df_copy

def create_providers_with_embeddings(input_csv: str = "data/providers.csv", output_csv: str = "data/providers_with_embeddings.csv"):

    if os.path.exists(output_csv):
        print(f"File {output_csv} already exists. Skipping embedding generation.")
        return
    
    print(f"Loading data from {input_csv}")
    df = pd.read_csv(input_csv)
    
    # Define columns to embed (text-heavy columns)
    text_columns_to_embed = [
        'specialties',
        'conditions', 
        'hospital_names',
        'system_names',
        'cities',
        'states'
    ]
    
    print(f"Starting embedding generation for {len(text_columns_to_embed)} columns...")
    df_with_embeddings = embed_text_columns(df, text_columns_to_embed)
    
    print(f"Saving results to {output_csv}")
    df_with_embeddings.to_csv(output_csv, index=False)
    print("Embedding generation complete!")
    
    return df_with_embeddings

def find_semantic_matches(query_terms: List[str], target_embeddings: List[List[float]], target_texts: List[str], threshold: float = 0.7) -> List[int]:
    print(f"    find_semantic_matches called with {len(query_terms)} query terms, {len(target_embeddings)} targets")
    
    if not query_terms or not target_embeddings:
        print("    No query terms or target embeddings, returning empty")
        return []
    
    query_embeddings = []
    for term in query_terms:
        if term and term.strip():
            print(f"    Generating embedding for: '{term}'")
            query_embeddings.append(generate_embedding(term.strip()))
    
    if not query_embeddings:
        print("    No valid query embeddings generated")
        return []
    
    matching_indices = set()
    all_matches = []
    
    for query_embedding in query_embeddings:
        if not query_embedding:
            continue
            
        for i, target_embedding in enumerate(target_embeddings):
            if not target_embedding:
                continue
            
            # Handle both single embeddings and lists of embeddings
            if isinstance(target_embedding[0], list):
                # Multiple embeddings - find the best match among them
                best_similarity = 0
                best_text = target_texts[i] if i < len(target_texts) else "N/A"
                
                for sub_embedding in target_embedding:
                    if sub_embedding:
                        similarity = compute_similarity(query_embedding, sub_embedding)
                        if similarity > best_similarity:
                            best_similarity = similarity
                
                all_matches.append((best_similarity, i, best_text))
                
                if best_similarity >= threshold:
                    matching_indices.add(i)
            else:
                # Single embedding
                similarity = compute_similarity(query_embedding, target_embedding)
                all_matches.append((similarity, i, target_texts[i] if i < len(target_texts) else "N/A"))
                
                if similarity >= threshold:
                    matching_indices.add(i)
    
    # Show ALL matches sorted by similarity
    all_matches.sort(reverse=True)
    print(f"    ALL SIMILARITY SCORES (threshold={threshold}):")
    for similarity, idx, text in all_matches:
        status = "✅ MATCH" if similarity >= threshold else "❌ below"
        print(f"      {similarity:.3f} {status}: {text}")
    
    print(f"    Found {len(matching_indices)} matches above threshold")
    return list(matching_indices)

def semantic_filter_dataframe(df: pd.DataFrame, specialty_terms: List[str] = None, condition_terms: List[str] = None, threshold: float = 0.7) -> pd.DataFrame:
    print(f"  semantic_filter_dataframe: {len(df)} rows, specialty_terms={specialty_terms}, condition_terms={condition_terms}")
    
    if not specialty_terms and not condition_terms:
        print("  No semantic terms provided, returning original dataframe")
        return df
    
    matching_indices = set(range(len(df)))
    print(f"  Starting with all {len(matching_indices)} indices")
    
    if specialty_terms:
        print(f"  Processing specialty terms: {specialty_terms}")
        specialty_embeddings = df['specialties_embedding'].tolist()
        specialty_texts = df['specialties'].tolist()
        print(f"  Loaded {len(specialty_embeddings)} specialty embeddings")
        
        # Check if embeddings are valid
        valid_embeddings = sum(1 for emb in specialty_embeddings if emb and len(emb) > 0)
        print(f"  {valid_embeddings} valid specialty embeddings found")
        
        specialty_matches = find_semantic_matches(specialty_terms, specialty_embeddings, specialty_texts, threshold)
        matching_indices &= set(specialty_matches)
        print(f"  After specialty filter: {len(matching_indices)} indices remain")
    
    if condition_terms:
        print(f"  Processing condition terms: {condition_terms}")
        condition_embeddings = df['conditions_embedding'].tolist()
        condition_texts = df['conditions'].tolist()
        print(f"  Loaded {len(condition_embeddings)} condition embeddings")
        
        # Check if embeddings are valid
        valid_embeddings = sum(1 for emb in condition_embeddings if emb and len(emb) > 0)
        print(f"  {valid_embeddings} valid condition embeddings found")
        
        condition_matches = find_semantic_matches(condition_terms, condition_embeddings, condition_texts, threshold)
        matching_indices &= set(condition_matches)
        print(f"  After condition filter: {len(matching_indices)} indices remain")
    
    if matching_indices:
        result = df.iloc[list(matching_indices)]
        print(f"  Returning {len(result)} matching rows")
        return result
    else:
        print("  No matches found, returning empty dataframe")
        return df.iloc[0:0]
