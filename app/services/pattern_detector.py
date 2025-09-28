"""
Pattern detection service for learning and identifying compliance violation patterns.
Uses machine learning to detect similar violations automatically.
"""
import os
import re
import json
import logging
import pickle
from typing import List, Dict, Set, Tuple, Optional
from datetime import datetime
from collections import defaultdict, Counter
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.cluster import DBSCAN
import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords

logger = logging.getLogger(__name__)

# Download required NLTK data
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')
    
try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords')


class PatternDetector:
    """Service for detecting and learning compliance violation patterns."""
    
    def __init__(self):
        """Initialize the pattern detector."""
        self.patterns_file = "data/models/violation_patterns.json"
        self.vectorizer_file = "data/models/pattern_vectorizer.pkl"
        self.violation_patterns = defaultdict(lambda: {
            'examples': [],
            'keywords': set(),
            'regex_patterns': [],
            'confidence': 0.0,
            'detection_count': 0
        })
        self.vectorizer = None
        self.pattern_vectors = None
        self.stop_words = set(stopwords.words('english'))
        self._load_patterns()
    
    def _load_patterns(self):
        """Load existing patterns from file."""
        # Load patterns
        if os.path.exists(self.patterns_file):
            try:
                with open(self.patterns_file, 'r') as f:
                    patterns = json.load(f)
                    for pattern_id, data in patterns.items():
                        self.violation_patterns[pattern_id] = {
                            'examples': data['examples'],
                            'keywords': set(data['keywords']),
                            'regex_patterns': data['regex_patterns'],
                            'confidence': data['confidence'],
                            'detection_count': data['detection_count']
                        }
                logger.info(f"Loaded {len(self.violation_patterns)} violation patterns")
            except Exception as e:
                logger.error(f"Failed to load patterns: {e}")
        
        # Load vectorizer
        if os.path.exists(self.vectorizer_file):
            try:
                with open(self.vectorizer_file, 'rb') as f:
                    self.vectorizer = pickle.load(f)
                logger.info("Loaded pattern vectorizer")
            except Exception as e:
                logger.error(f"Failed to load vectorizer: {e}")
    
    def _save_patterns(self):
        """Save patterns to file."""
        try:
            os.makedirs(os.path.dirname(self.patterns_file), exist_ok=True)
            
            # Convert sets to lists for JSON serialization
            patterns_data = {}
            for pattern_id, data in self.violation_patterns.items():
                patterns_data[pattern_id] = {
                    'examples': data['examples'],
                    'keywords': list(data['keywords']),
                    'regex_patterns': data['regex_patterns'],
                    'confidence': data['confidence'],
                    'detection_count': data['detection_count']
                }
            
            with open(self.patterns_file, 'w') as f:
                json.dump(patterns_data, f, indent=2)
            
            # Save vectorizer
            if self.vectorizer:
                with open(self.vectorizer_file, 'wb') as f:
                    pickle.dump(self.vectorizer, f)
                    
        except Exception as e:
            logger.error(f"Failed to save patterns: {e}")
    
    async def learn_from_violation(self, text: str, violation_type: str, confidence: float = 0.8):
        """
        Learn from a new violation example.
        
        Args:
            text: The text containing the violation
            violation_type: Type of violation (e.g., 'misleading_claim', 'unauthorized_offer')
            confidence: Confidence score of the violation
        """
        # Extract features from text
        keywords = self._extract_keywords(text)
        patterns = self._extract_patterns(text)
        
        # Update violation patterns
        pattern_data = self.violation_patterns[violation_type]
        pattern_data['examples'].append({
            'text': text[:500],  # Store first 500 chars
            'timestamp': datetime.now().isoformat(),
            'confidence': confidence
        })
        
        # Keep only last 100 examples
        if len(pattern_data['examples']) > 100:
            pattern_data['examples'] = pattern_data['examples'][-100:]
        
        # Update keywords
        pattern_data['keywords'].update(keywords)
        
        # Update regex patterns
        for pattern in patterns:
            if pattern not in pattern_data['regex_patterns']:
                pattern_data['regex_patterns'].append(pattern)
        
        # Update confidence (weighted average)
        pattern_data['detection_count'] += 1
        pattern_data['confidence'] = (
            (pattern_data['confidence'] * (pattern_data['detection_count'] - 1) + confidence) /
            pattern_data['detection_count']
        )
        
        # Retrain vectorizer if we have enough examples
        if len(pattern_data['examples']) >= 10:
            await self._update_pattern_model()
        
        self._save_patterns()
    
    def _extract_keywords(self, text: str) -> Set[str]:
        """Extract important keywords from text."""
        # Tokenize and clean
        tokens = word_tokenize(text.lower())
        
        # Remove stopwords and short tokens
        keywords = {
            token for token in tokens
            if token not in self.stop_words and len(token) > 3 and token.isalpha()
        }
        
        # Extract important phrases
        important_phrases = [
            'guaranteed profit', 'risk free', 'exclusive offer',
            'limited time', 'act now', 'don\'t miss', 'secret method',
            'make money fast', 'financial freedom', 'passive income'
        ]
        
        for phrase in important_phrases:
            if phrase in text.lower():
                keywords.add(phrase.replace(' ', '_'))
        
        return keywords
    
    def _extract_patterns(self, text: str) -> List[str]:
        """Extract regex patterns from text."""
        patterns = []
        
        # Common violation patterns
        pattern_templates = [
            r'\b(?:earn|make|profit)\s+\$?\d+(?:k|K|,\d{3})?\s*(?:per|a|in)\s*(?:day|week|month)\b',
            r'\b(?:guaranteed|promise|ensure)\s+(?:profit|return|income)\b',
            r'\b(?:risk[\s-]?free|no[\s-]?risk)\s+(?:trading|investment|opportunity)\b',
            r'\b(?:exclusive|limited|special)\s+(?:offer|deal|opportunity)\b',
            r'\b(?:act|sign[\s-]?up|register)\s+(?:now|today|immediately)\b',
            r'\b(?:secret|hidden|insider)\s+(?:method|strategy|technique)\b'
        ]
        
        for pattern in pattern_templates:
            if re.search(pattern, text, re.IGNORECASE):
                patterns.append(pattern)
        
        return patterns
    
    async def detect_patterns(self, text: str) -> List[Dict]:
        """
        Detect known violation patterns in text.
        
        Returns:
            List of detected patterns with confidence scores
        """
        detected_patterns = []
        
        # Check each known pattern
        for violation_type, pattern_data in self.violation_patterns.items():
            score = 0.0
            matches = []
            
            # Check keywords
            text_lower = text.lower()
            keyword_matches = sum(1 for keyword in pattern_data['keywords'] if keyword in text_lower)
            if keyword_matches > 0:
                keyword_score = min(keyword_matches / max(len(pattern_data['keywords']), 1), 1.0)
                score += keyword_score * 0.4
                matches.append(f"Keywords: {keyword_matches} matches")
            
            # Check regex patterns
            regex_matches = 0
            for pattern in pattern_data['regex_patterns']:
                if re.search(pattern, text, re.IGNORECASE):
                    regex_matches += 1
                    matches.append(f"Pattern: {pattern}")
            
            if regex_matches > 0:
                regex_score = min(regex_matches / max(len(pattern_data['regex_patterns']), 1), 1.0)
                score += regex_score * 0.6
            
            # Use vectorizer for similarity if available
            if self.vectorizer and len(pattern_data['examples']) >= 5:
                similarity_score = await self._calculate_similarity(text, violation_type)
                if similarity_score > 0.5:
                    score = max(score, similarity_score)
                    matches.append(f"Similarity: {similarity_score:.2f}")
            
            # Add detection if score is significant
            if score > 0.3:
                detected_patterns.append({
                    'violation_type': violation_type,
                    'confidence': min(score * pattern_data['confidence'], 0.95),
                    'matches': matches,
                    'pattern_confidence': pattern_data['confidence'],
                    'detection_count': pattern_data['detection_count']
                })
        
        # Sort by confidence
        detected_patterns.sort(key=lambda x: x['confidence'], reverse=True)
        
        return detected_patterns
    
    async def _calculate_similarity(self, text: str, violation_type: str) -> float:
        """Calculate similarity between text and known violation examples."""
        try:
            pattern_data = self.violation_patterns[violation_type]
            example_texts = [ex['text'] for ex in pattern_data['examples'][-20:]]  # Use last 20 examples
            
            if not example_texts:
                return 0.0
            
            # Create or update vectorizer
            if not self.vectorizer:
                self.vectorizer = TfidfVectorizer(
                    max_features=1000,
                    ngram_range=(1, 3),
                    stop_words='english'
                )
                example_vectors = self.vectorizer.fit_transform(example_texts)
            else:
                example_vectors = self.vectorizer.transform(example_texts)
            
            # Transform input text
            text_vector = self.vectorizer.transform([text])
            
            # Calculate similarities
            similarities = cosine_similarity(text_vector, example_vectors)[0]
            
            # Return max similarity
            return float(np.max(similarities))
            
        except Exception as e:
            logger.error(f"Error calculating similarity: {e}")
            return 0.0
    
    async def _update_pattern_model(self):
        """Update the pattern detection model with new examples."""
        try:
            # Collect all examples
            all_texts = []
            all_labels = []
            
            for violation_type, pattern_data in self.violation_patterns.items():
                for example in pattern_data['examples']:
                    all_texts.append(example['text'])
                    all_labels.append(violation_type)
            
            if len(all_texts) < 20:
                return
            
            # Update vectorizer
            self.vectorizer = TfidfVectorizer(
                max_features=1000,
                ngram_range=(1, 3),
                stop_words='english'
            )
            
            self.pattern_vectors = self.vectorizer.fit_transform(all_texts)
            
            logger.info(f"Updated pattern model with {len(all_texts)} examples")
            
        except Exception as e:
            logger.error(f"Error updating pattern model: {e}")
    
    def get_pattern_statistics(self) -> Dict:
        """Get statistics about learned patterns."""
        stats = {
            'total_patterns': len(self.violation_patterns),
            'total_examples': sum(len(p['examples']) for p in self.violation_patterns.values()),
            'patterns_by_type': {},
            'most_common_keywords': Counter(),
            'high_confidence_patterns': []
        }
        
        # Analyze each pattern type
        for violation_type, pattern_data in self.violation_patterns.items():
            stats['patterns_by_type'][violation_type] = {
                'examples': len(pattern_data['examples']),
                'keywords': len(pattern_data['keywords']),
                'regex_patterns': len(pattern_data['regex_patterns']),
                'confidence': pattern_data['confidence'],
                'detections': pattern_data['detection_count']
            }
            
            # Collect keywords
            stats['most_common_keywords'].update(pattern_data['keywords'])
            
            # High confidence patterns
            if pattern_data['confidence'] > 0.8 and pattern_data['detection_count'] > 5:
                stats['high_confidence_patterns'].append({
                    'type': violation_type,
                    'confidence': pattern_data['confidence'],
                    'detections': pattern_data['detection_count']
                })
        
        # Get top keywords
        stats['most_common_keywords'] = dict(stats['most_common_keywords'].most_common(20))
        
        return stats
    
    async def suggest_new_patterns(self, texts: List[str]) -> List[Dict]:
        """
        Analyze texts to suggest new patterns that might be violations.
        Uses clustering to find groups of similar suspicious content.
        """
        if len(texts) < 10:
            return []
        
        try:
            # Vectorize texts
            vectorizer = TfidfVectorizer(
                max_features=500,
                ngram_range=(1, 3),
                stop_words='english'
            )
            vectors = vectorizer.fit_transform(texts)
            
            # Cluster similar texts
            clustering = DBSCAN(eps=0.3, min_samples=3, metric='cosine')
            clusters = clustering.fit_predict(vectors)
            
            # Analyze clusters
            suggestions = []
            unique_clusters = set(clusters)
            unique_clusters.discard(-1)  # Remove noise cluster
            
            for cluster_id in unique_clusters:
                cluster_indices = [i for i, c in enumerate(clusters) if c == cluster_id]
                cluster_texts = [texts[i] for i in cluster_indices]
                
                # Extract common features
                common_keywords = self._find_common_keywords(cluster_texts)
                
                if common_keywords:
                    suggestions.append({
                        'cluster_id': int(cluster_id),
                        'size': len(cluster_texts),
                        'common_keywords': list(common_keywords)[:10],
                        'sample_texts': cluster_texts[:3],
                        'suggested_pattern_name': f"pattern_cluster_{cluster_id}"
                    })
            
            return suggestions
            
        except Exception as e:
            logger.error(f"Error suggesting patterns: {e}")
            return []
    
    def _find_common_keywords(self, texts: List[str]) -> Set[str]:
        """Find keywords common to multiple texts."""
        keyword_counts = Counter()
        
        for text in texts:
            keywords = self._extract_keywords(text)
            keyword_counts.update(keywords)
        
        # Return keywords that appear in at least 50% of texts
        threshold = len(texts) * 0.5
        return {keyword for keyword, count in keyword_counts.items() if count >= threshold}


# Singleton instance
pattern_detector = PatternDetector() 