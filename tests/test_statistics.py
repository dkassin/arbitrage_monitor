import pytest
from decimal import Decimal
from src.core.statistics import StreamingStats


class TestStreamingStats:
    
    def test_tracks_max_bid_price(self):
        stats = StreamingStats("test_exchange")
        
        stats.update_bid(Decimal("110000"), Decimal("1.0"))
        stats.update_bid(Decimal("110500"), Decimal("1.0"))
        stats.update_bid(Decimal("110200"), Decimal("1.0"))
        
        assert stats.max_bid_price == Decimal("110500")
    
    def test_tracks_max_price_change(self):
        stats = StreamingStats("test_exchange")
        
        stats.update_bid(Decimal("110000"), Decimal("1.0"))
        stats.update_bid(Decimal("110100"), Decimal("1.0"))  
        stats.update_bid(Decimal("110020"), Decimal("1.0")) 
        
        # Max change should be 100
        assert stats.max_bid_price_change == Decimal("100")
    
    def test_accumulates_volume(self):
        stats = StreamingStats("test_exchange")
        
        stats.update_bid(Decimal("110000"), Decimal("1.5"))
        stats.update_bid(Decimal("110000"), Decimal("2.3"))
        stats.update_bid(Decimal("110000"), Decimal("0.7"))
        
        assert stats.total_volume_at_best_bid == Decimal("4.5")
    
    def test_ignores_none_values(self):
        stats = StreamingStats("test_exchange")
        
        stats.update_bid(Decimal("110000"), Decimal("1.0"))
        # Next two Should be ignored
        stats.update_bid(None, Decimal("1.0"))
        stats.update_bid(Decimal("110000"), None)  
        
        # Only first update should count
        assert stats.total_volume_at_best_bid == Decimal("1.0")
        assert stats.max_bid_price == Decimal("110000")
    
    def test_ignores_invalid_values(self):
        stats = StreamingStats("test_exchange")
        
        stats.update_bid(Decimal("110000"), Decimal("1.0"))
        # Invalid price
        stats.update_bid(Decimal("0"), Decimal("1.0"))  
        # Negative price
        stats.update_bid(Decimal("-100"), Decimal("1.0"))  
        # Zero volume
        stats.update_bid(Decimal("110000"), Decimal("0"))  
        
        # Only first valid update should count
        assert stats.total_volume_at_best_bid == Decimal("1.0")
    
    def test_get_stats_format(self):
        stats = StreamingStats("kraken")
        
        stats.update_bid(Decimal("110000"), Decimal("1.5"))
        stats.update_bid(Decimal("110100"), Decimal("2.0"))
        
        result = stats.get_stats()
        
        assert result["exchange"] == "kraken"
        assert isinstance(result["max_bid_price_change"], float)
        assert isinstance(result["total_volume_at_best_bid"], float)
        assert isinstance(result["max_bid_price"], float)
        assert result["max_bid_price"] == 110100.0