#!/usr/bin/env python3
"""
Analyze the current status of the URL Checker system.
Provides insights into:
- Blacklist statistics
- Pinecone vector database status
- Processing analytics
- Domain reputation
"""
import os
import sys
import csv
import json
import asyncio
from datetime import datetime
from collections import Counter, defaultdict
from urllib.parse import urlparse

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.vector_db import pinecone_service
from app.core.blacklist_manager import blacklist_manager
from app.services.database import database_service


async def analyze_blacklist():
    """Analyze the blacklist file and provide statistics."""
    print("\n" + "="*80)
    print("📊 BLACKLIST ANALYSIS")
    print("="*80)
    
    blacklist_file = "data/tmp/blacklist_consolidated.csv"
    
    if not os.path.exists(blacklist_file):
        print("❌ Blacklist file not found!")
        return
    
    # Read blacklist data
    domains = Counter()
    reasons = Counter()
    categories = Counter()
    analysis_methods = Counter()
    confidence_scores = []
    
    with open(blacklist_file, 'r', newline='') as f:
        reader = csv.DictReader(f)
        total_entries = 0
        
        for row in reader:
            total_entries += 1
            
            # Count domains
            if 'Main Domain' in row:
                domains[row['Main Domain']] += 1
            
            # Count reasons
            if 'Reason' in row and row['Reason']:
                # Extract analysis method from reason
                reason = row['Reason']
                if 'real_llm:' in reason:
                    analysis_methods['real_llm'] += 1
                elif 'openai:' in reason:
                    analysis_methods['openai'] += 1
                elif 'fallback:' in reason:
                    analysis_methods['fallback'] += 1
                
                # Clean reason for counting
                clean_reason = reason.split(':', 1)[-1].strip() if ':' in reason else reason
                reasons[clean_reason[:50] + '...'] += 1
            
            # Count categories
            if 'Category' in row:
                categories[row['Category']] += 1
            
            # Collect confidence scores
            if 'Confidence' in row and row['Confidence']:
                try:
                    confidence_scores.append(float(row['Confidence']))
                except ValueError:
                    pass
    
    # Display statistics
    print(f"\n📈 Total Blacklisted URLs: {total_entries}")
    print(f"📈 Unique Domains: {len(domains)}")
    
    print("\n🔝 Top 10 Blacklisted Domains:")
    for domain, count in domains.most_common(10):
        print(f"   - {domain}: {count} URLs")
    
    print("\n📊 Analysis Methods Used:")
    for method, count in analysis_methods.items():
        percentage = (count / total_entries * 100) if total_entries > 0 else 0
        print(f"   - {method}: {count} ({percentage:.1f}%)")
    
    print("\n📊 Categories:")
    for category, count in categories.items():
        percentage = (count / total_entries * 100) if total_entries > 0 else 0
        print(f"   - {category}: {count} ({percentage:.1f}%)")
    
    if confidence_scores:
        avg_confidence = sum(confidence_scores) / len(confidence_scores)
        print(f"\n📊 Average Confidence Score: {avg_confidence:.2f}")
        print(f"   - Min: {min(confidence_scores):.2f}")
        print(f"   - Max: {max(confidence_scores):.2f}")
    
    # Get blacklist analytics from manager
    analytics = await blacklist_manager.get_blacklist_analytics()
    
    print("\n🔍 Violation Types (Top 10):")
    for violation in analytics['top_violations'][:10]:
        print(f"   - {violation['type']}: {violation['count']} occurrences")
    
    print("\n📊 Domains by Confidence Level:")
    print(f"   - High (0.8-1.0): {analytics['domains_by_confidence']['high']} domains")
    print(f"   - Medium (0.5-0.8): {analytics['domains_by_confidence']['medium']} domains")
    print(f"   - Low (0.0-0.5): {analytics['domains_by_confidence']['low']} domains")
    
    print("\n🆕 Recent Additions (Last 7 days):")
    for addition in analytics['recent_additions'][:5]:
        print(f"   - {addition['domain']} (confidence: {addition['confidence']:.2f}, violations: {addition['violation_count']})")


async def analyze_pinecone():
    """Analyze Pinecone vector database status."""
    print("\n" + "="*80)
    print("🔍 PINECONE VECTOR DATABASE ANALYSIS")
    print("="*80)
    
    if not pinecone_service.is_initialized:
        print("❌ Pinecone service not initialized!")
        return
    
    try:
        # Get index stats
        stats = pinecone_service.index.describe_index_stats()
        
        print(f"\n📊 Index Name: url-checker-index")
        print(f"📊 Total Vectors: {stats.total_vector_count:,}")
        
        if hasattr(stats, 'namespaces') and stats.namespaces:
            print("\n📊 Namespaces:")
            for ns_name, ns_stats in stats.namespaces.items():
                print(f"   - {ns_name}: {ns_stats.vector_count:,} vectors")
        
        # Sample some vectors to analyze
        print("\n🔍 Analyzing vector metadata...")
        
        # Query for a sample of vectors
        sample_results = pinecone_service.index.query(
            vector=[0.0] * 384,  # Dummy vector for metadata-only query
            top_k=100,
            include_metadata=True
        )
        
        if sample_results.matches:
            urls = set()
            domains = Counter()
            
            for match in sample_results.matches:
                if match.metadata:
                    url = match.metadata.get('url', '')
                    if url:
                        urls.add(url)
                        domain = urlparse(url).netloc
                        domains[domain] += 1
            
            print(f"📊 Unique URLs in sample: {len(urls)}")
            print(f"📊 Unique domains in sample: {len(domains)}")
            
            print("\n🔝 Top domains in vector database (from sample):")
            for domain, count in domains.most_common(10):
                print(f"   - {domain}: {count} vectors")
    
    except Exception as e:
        print(f"❌ Error analyzing Pinecone: {str(e)}")


async def analyze_database():
    """Analyze the SQLite database for processing statistics."""
    print("\n" + "="*80)
    print("💾 DATABASE ANALYSIS")
    print("="*80)
    
    try:
        # Get batch count
        batch_count = await database_service.get_batch_count()
        print(f"\n📊 Total Batches: {batch_count}")
        
        # Get URL count by status
        url_count = await database_service.get_url_count()
        print(f"📊 Total URLs in Database: {url_count}")
        
        # Get recent batches
        recent_batches = await database_service.get_recent_batches(limit=5)
        if recent_batches:
            print("\n📊 Recent Batches:")
            for batch in recent_batches:
                print(f"   - {batch.id}: {batch.url_count} URLs ({batch.status})")
        
        # Check if database file exists and get its size
        db_path = "data/db/url_checker.db"
        if os.path.exists(db_path):
            db_size = os.path.getsize(db_path) / (1024 * 1024)  # Convert to MB
            print(f"\n📊 Database Size: {db_size:.2f} MB")
    
    except Exception as e:
        print(f"❌ Error analyzing database: {str(e)}")


async def main():
    """Run all analyses."""
    print("\n" + "="*80)
    print("🚀 URL CHECKER SYSTEM STATUS ANALYSIS")
    print(f"📅 Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)
    
    # Run analyses
    await analyze_blacklist()
    await analyze_pinecone()
    await analyze_database()
    
    print("\n" + "="*80)
    print("✅ Analysis Complete!")
    print("="*80)


if __name__ == "__main__":
    asyncio.run(main()) 