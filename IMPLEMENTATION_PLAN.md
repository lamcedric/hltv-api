# HLTV Match Scraper - Implementation Plan

## Project Goal
Transform the existing HLTV-API into a Docker service that scrapes ALL historical CS:GO/CS2 match data for machine learning prediction pipelines.

---

## Current State Analysis

### What Exists
- FastAPI-based web scraper for HLTV player and event data
- On-demand scraping with Pydantic models (no data persistence)
- Cloudflare bypass using cloudscraper
- Docker-ready deployment
- Endpoints for: Players, Events, Team Stats

### Tech Stack
- **Framework**: FastAPI + Uvicorn
- **Scraping**: BeautifulSoup4, lxml, cloudscraper
- **Validation**: Pydantic v2
- **Deployment**: Docker, Fly.io

### What's Missing
- Match data scraping (core requirement)
- Historical match pagination
- Data persistence (CSV/Postgres)
- Batch scraping capabilities
- Update mechanisms for new matches

---

## Data Requirements for ML Pipeline

### Match-Level Data
- `match_id` - Unique identifier
- `date` - Match date/time
- `event_id` - Tournament/event identifier
- `event_name` - Tournament name
- `format` - BO1, BO3, BO5
- `team1_id`, `team1_name`
- `team2_id`, `team2_name`
- `final_score` - e.g., "2-1", "16-14" for BO1
- `winner_id` - Winning team ID
- `match_url` - HLTV match page URL

### Map-Level Data
- `map_id` - Unique identifier
- `match_id` - Foreign key to match
- `map_number` - Order in series (1, 2, 3)
- `map_name` - Dust2, Mirage, Inferno, Nuke, Overpass, Vertigo, Ancient, Anubis
- `team1_score` - Rounds won by team 1
- `team2_score` - Rounds won by team 2
- `winner_id` - Map winner
- `map_pick` - Which team picked (if available)

### Player Performance Data (Per Map/Match)
- `player_id` - Player identifier
- `player_name` - In-game name
- `team_id` - Team identifier
- `match_id` - Foreign key
- `map_id` - Foreign key (NULL for overall match stats)
- `kills` - Total kills
- `deaths` - Total deaths
- `assists` - Assist count
- `kd_ratio` - K/D ratio
- `adr` - Average damage per round
- `kast_percent` - KAST percentage
- `rating` - HLTV Rating 2.0
- `headshot_percent` - Headshot percentage
- `opening_kills` - First kills in rounds
- `opening_deaths` - First deaths in rounds
- `flash_assists` - Flash assist count
- `clutches_won` - Clutches won (1vX situations)
- `clutches_total` - Total clutch situations

### Team Metadata
- `team_id` - Unique identifier
- `team_name` - Team name
- `team_logo_url` - Logo image
- `team_country` - Country/region
- `team_rank` - HLTV ranking (if available)

### Player Metadata
- `player_id` - Unique identifier
- `player_name` - Nickname
- `real_name` - Full name
- `country` - Nationality
- `current_team_id` - Current team

---

## Database Schema Design

### PostgreSQL Tables

```sql
-- Matches table
CREATE TABLE matches (
    match_id SERIAL PRIMARY KEY,
    hltv_match_id VARCHAR(50) UNIQUE NOT NULL,
    date TIMESTAMP NOT NULL,
    event_id INTEGER,
    event_name VARCHAR(255),
    format VARCHAR(10),  -- 'bo1', 'bo3', 'bo5'
    team1_id INTEGER NOT NULL,
    team2_id INTEGER NOT NULL,
    final_score VARCHAR(20),  -- '2-1', '16-14', etc.
    winner_id INTEGER,
    match_url TEXT,
    scraped_at TIMESTAMP DEFAULT NOW(),
    INDEX idx_date (date),
    INDEX idx_teams (team1_id, team2_id),
    INDEX idx_event (event_id)
);

-- Maps table
CREATE TABLE maps (
    map_id SERIAL PRIMARY KEY,
    match_id INTEGER REFERENCES matches(match_id),
    map_number INTEGER,
    map_name VARCHAR(50),
    team1_score INTEGER,
    team2_score INTEGER,
    winner_id INTEGER,
    map_pick VARCHAR(10),  -- 'team1', 'team2', 'decider'
    INDEX idx_match (match_id),
    INDEX idx_map_name (map_name)
);

-- Player match statistics
CREATE TABLE player_stats (
    stat_id SERIAL PRIMARY KEY,
    match_id INTEGER REFERENCES matches(match_id),
    map_id INTEGER REFERENCES maps(map_id),  -- NULL for overall match stats
    player_id INTEGER NOT NULL,
    team_id INTEGER NOT NULL,
    kills INTEGER,
    deaths INTEGER,
    assists INTEGER,
    kd_ratio DECIMAL(4,2),
    adr DECIMAL(5,2),
    kast_percent DECIMAL(5,2),
    rating DECIMAL(4,2),
    headshot_percent DECIMAL(5,2),
    opening_kills INTEGER,
    opening_deaths INTEGER,
    flash_assists INTEGER,
    clutches_won INTEGER,
    clutches_total INTEGER,
    INDEX idx_player (player_id),
    INDEX idx_match (match_id),
    INDEX idx_map (map_id)
);

-- Teams metadata
CREATE TABLE teams (
    team_id SERIAL PRIMARY KEY,
    hltv_team_id VARCHAR(50) UNIQUE NOT NULL,
    team_name VARCHAR(255) NOT NULL,
    team_logo_url TEXT,
    team_country VARCHAR(100),
    team_rank INTEGER,
    last_updated TIMESTAMP DEFAULT NOW()
);

-- Players metadata
CREATE TABLE players (
    player_id SERIAL PRIMARY KEY,
    hltv_player_id VARCHAR(50) UNIQUE NOT NULL,
    player_name VARCHAR(255) NOT NULL,
    real_name VARCHAR(255),
    country VARCHAR(100),
    current_team_id INTEGER,
    last_updated TIMESTAMP DEFAULT NOW()
);
```

### CSV File Structure (For Testing Phase)

**matches.csv**
```
match_id,date,event_id,event_name,format,team1_id,team1_name,team2_id,team2_name,final_score,winner_id,match_url
```

**maps.csv**
```
map_id,match_id,map_number,map_name,team1_score,team2_score,winner_id,map_pick
```

**player_stats.csv**
```
stat_id,match_id,map_id,player_id,player_name,team_id,kills,deaths,assists,kd_ratio,adr,kast_percent,rating,headshot_percent,opening_kills,opening_deaths,flash_assists,clutches_won,clutches_total
```

**teams.csv**
```
team_id,hltv_team_id,team_name,team_logo_url,team_country,team_rank
```

**players.csv**
```
player_id,hltv_player_id,player_name,real_name,country,current_team_id
```

---

## Implementation Phases

### Phase 1: Repository Setup & Research
**Objective**: Understand HLTV match page structure

**Tasks**:
1. Fork repository to your GitHub account
2. Set up local development environment
3. Analyze HLTV match pages:
   - Results page structure: `/results`
   - Individual match page: `/matches/{id}/{slug}`
   - Pagination mechanism
   - Filter options (date range, teams, events)
4. Identify XPath selectors for:
   - Match metadata
   - Map results
   - Player statistics tables
   - Pagination controls

**Deliverables**:
- Forked repository
- Documentation of HLTV page structures
- XPath selector mappings

---

### Phase 2: Match Scraping Service
**Objective**: Create endpoints to scrape individual matches

**Tasks**:
1. Create new schemas in `app/schemas/matches/`:
   - `match.py` - Match model
   - `map.py` - Map model
   - `player_stats.py` - Player statistics model
2. Create service in `app/services/matches/`:
   - `details.py` - Match details scraper
   - `stats.py` - Player stats scraper
3. Add XPath selectors to `app/utils/xpath.py`
4. Create endpoints in `app/api/endpoints/matches.py`:
   ```python
   GET /matches/{match_id}/details
   GET /matches/{match_id}/maps
   GET /matches/{match_id}/stats
   ```
5. Unit tests for match scraping

**Deliverables**:
- Working match scraping endpoints
- Pydantic models for match data
- Test coverage

---

### Phase 3: Historical Match Scraper
**Objective**: Scrape all historical matches from HLTV

**Tasks**:
1. Create `app/services/matches/historical.py`:
   - Paginate through `/results` page
   - Extract match IDs from listing
   - Handle date range filtering
   - Implement rate limiting (avoid bans)
2. Create scraping worker:
   - `app/workers/scraper.py`
   - Progress tracking (save position)
   - Resume capability after interruption
   - Error handling and retry logic
3. Add endpoint for triggering historical scrape:
   ```python
   POST /matches/scrape/historical
   {
     "start_date": "2020-01-01",
     "end_date": "2024-12-31",
     "batch_size": 100
   }
   ```
4. Logging and monitoring:
   - Track scraping progress
   - Log errors and skipped matches
   - Estimate completion time

**Deliverables**:
- Historical scraper worker
- Progress tracking mechanism
- API endpoint to trigger/monitor scraping

---

### Phase 4: Data Persistence Layer
**Objective**: Implement dual storage (CSV + Postgres)

**Tasks**:
1. Create storage abstraction layer:
   ```python
   # app/storage/base.py
   class StorageBackend(ABC):
       @abstractmethod
       def save_match(self, match_data): pass
       @abstractmethod
       def save_maps(self, maps_data): pass
       @abstractmethod
       def save_player_stats(self, stats_data): pass
       @abstractmethod
       def get_last_scraped_date(self): pass
   ```

2. Implement CSV storage:
   ```python
   # app/storage/csv_storage.py
   class CSVStorage(StorageBackend):
       # Write to CSV files with append mode
       # Handle deduplication
       # Implement file rotation for large datasets
   ```

3. Implement Postgres storage:
   ```python
   # app/storage/postgres_storage.py
   class PostgresStorage(StorageBackend):
       # SQLAlchemy models
       # Batch insert operations
       # Transaction handling
   ```

4. Add storage configuration:
   ```python
   # app/settings.py
   STORAGE_BACKEND = 'csv'  # or 'postgres'
   CSV_OUTPUT_DIR = './data'
   DATABASE_URL = 'postgresql://user:pass@localhost/hltv'
   ```

5. Modify scraping services to use storage backend

**Deliverables**:
- Storage abstraction layer
- CSV and Postgres implementations
- Configuration management
- Data export functionality

---

### Phase 5: Dockerization
**Objective**: Create production-ready Docker service

**Tasks**:
1. Update `Dockerfile`:
   - Add dependencies for Postgres (psycopg2)
   - Create data volume mount point
   - Environment variable configuration

2. Create `docker-compose.yml`:
   ```yaml
   version: '3.8'
   services:
     api:
       build: .
       ports:
         - "8000:8000"
       environment:
         - STORAGE_BACKEND=csv
         - CSV_OUTPUT_DIR=/data
       volumes:
         - ./data:/data

     scraper:
       build: .
       command: python -m app.workers.scraper
       environment:
         - STORAGE_BACKEND=csv
       volumes:
         - ./data:/data
       depends_on:
         - api

     postgres:
       image: postgres:15-alpine
       environment:
         - POSTGRES_DB=hltv
         - POSTGRES_USER=hltv
         - POSTGRES_PASSWORD=hltv_password
       volumes:
         - pgdata:/var/lib/postgresql/data
       ports:
         - "5432:5432"

   volumes:
     pgdata:
   ```

3. Create environment files:
   - `.env.example` - Template configuration
   - `.env.csv` - CSV mode configuration
   - `.env.postgres` - Postgres mode configuration

4. Update README with Docker instructions

**Deliverables**:
- Production Dockerfile
- Docker Compose configuration
- Environment templates
- Updated documentation

---

### Phase 6: Update Mechanism
**Objective**: Continuously update with new matches

**Tasks**:
1. Create incremental scraper:
   ```python
   # app/workers/incremental_scraper.py
   # Check for new matches since last scrape
   # Run on schedule (daily/hourly)
   ```

2. Implement deduplication:
   - Check if match already exists before scraping
   - Update existing records if data changed
   - Skip already-processed matches

3. Add scheduling options:
   - Cron job integration
   - APScheduler for background tasks
   - Manual trigger endpoint

4. Data validation:
   - Verify match completeness
   - Flag anomalies (missing maps, stats)
   - Generate data quality reports

**Deliverables**:
- Incremental update worker
- Deduplication logic
- Scheduling mechanism
- Data validation reports

---

### Phase 7: Testing & Migration
**Objective**: Production readiness and Postgres migration

**Tasks**:
1. Test with sample dataset:
   - Scrape last 3 months of matches
   - Verify CSV output correctness
   - Check data integrity

2. Full historical scrape (CSV mode):
   - Run complete historical scrape
   - Monitor for errors
   - Generate statistics report

3. Migrate to Postgres:
   - Import CSV data into Postgres
   - Verify data consistency
   - Create database indexes
   - Run performance tests

4. Create data export utilities:
   - Export Postgres → CSV for ML pipeline
   - Generate training/test split datasets
   - Create data dictionaries

5. Documentation:
   - API documentation (OpenAPI/Swagger)
   - Data schema documentation
   - Deployment guide
   - Troubleshooting guide

**Deliverables**:
- Complete historical dataset (CSV)
- Postgres database with all data
- Export utilities
- Comprehensive documentation

---

## Implementation Timeline

### Week 1: Foundation ✅ COMPLETED
- [x] Fork repository
- [x] Analyze HLTV match pages
- [x] Design database schema (finalize)
- [x] Set up development environment

### Week 2: Core Scraping ✅ COMPLETED
- [x] Create match schemas (`app/schemas/matches/match.py`)
- [x] Implement match scraping service (`app/services/matches/`)
- [x] Build match endpoints (`app/api/endpoints/matches.py`)
- [x] Test with sample matches

### Week 3: Historical Scraper ✅ COMPLETED
- [x] Implement pagination logic (in HLTVMatchResults)
- [x] Build historical scraper worker (`app/workers/scraper.py`)
- [x] Add progress tracking (with resume capability)
- [x] Test with date ranges

### Week 4: Data Layer ✅ COMPLETED
- [x] Create storage abstraction (`app/storage/base.py`)
- [x] Implement CSV storage (`app/storage/csv_storage.py`)
- [ ] Implement Postgres storage (optional, for production)
- [x] Add configuration management (`.env.example`)

### Week 5: Dockerization ✅ COMPLETED
- [x] Update Dockerfile
- [x] Create Docker Compose (`docker-compose.yml`)
- [ ] Test container deployment
- [x] Document deployment process

### Week 6: Updates & Testing ✅ COMPLETED
- [x] Build incremental scraper (`app/workers/incremental.py`)
- [x] Add deduplication (in CSVStorage)
- [ ] Run full historical scrape
- [x] Validate data quality (tested with sample match)

### Week 7: Production
- [ ] Migrate to Postgres (optional)
- [x] Create export utilities (CSV export in storage)
- [ ] Performance optimization
- [ ] Final documentation

---

## Key Considerations

### Rate Limiting
- HLTV has Cloudflare protection (handled by cloudscraper)
- Implement delays between requests (2-3 seconds recommended)
- Use exponential backoff on errors
- Consider scraping during off-peak hours

### Data Quality
- Some older matches may have incomplete data
- Handle missing statistics gracefully
- Log data quality issues for manual review
- Implement data validation rules

### Storage Strategy
- **CSV Mode**: Best for initial testing, easy inspection, ML pipeline integration
- **Postgres Mode**: Better for large datasets, complex queries, data updates
- Consider hybrid: Postgres for storage, CSV exports for ML pipeline

### Performance Optimization
- Batch database inserts (1000 records at a time)
- Use database connection pooling
- Implement caching for frequently accessed data
- Parallelize scraping where possible (careful with rate limits)

### Error Handling
- Network errors: Retry with exponential backoff
- Missing data: Log and continue (don't fail entire scrape)
- Cloudflare blocks: Increase delays, rotate user agents
- Parse errors: Save raw HTML for debugging

---

## API Endpoints Summary

### Match Endpoints (New)
```
GET  /matches/{match_id}/details      - Get match details
GET  /matches/{match_id}/maps         - Get map results
GET  /matches/{match_id}/stats        - Get player statistics
POST /matches/scrape/historical       - Trigger historical scrape
GET  /matches/scrape/status           - Check scraping progress
POST /matches/scrape/incremental      - Update with new matches
GET  /matches/export/csv              - Export data to CSV
```

### Existing Endpoints (Keep)
```
GET /players/search/{name}
GET /players/{id}/profile
GET /players/{id}/stats
GET /events/search/{name}
GET /events/{id}/profile
GET /events/{id}/team/{team_id}/stats
```

---

## Expected Data Volume

### Historical Matches Estimate
- HLTV has matches dating back to ~2010
- Approximately **150,000-200,000** professional matches
- **3-5 maps per match** on average
- **10 players per match** (5 per team)

### Storage Requirements
- **CSV**: ~5-10 GB for all historical data
- **Postgres**: ~10-15 GB with indexes
- Recommend **50 GB** disk space for safety margin

### Scraping Time Estimate
- **Rate**: ~200-300 matches per hour (with rate limiting)
- **Total time**: 25-40 days of continuous scraping for all history
- Can parallelize with multiple workers if needed

---

## Success Criteria

- [ ] All historical matches scraped (2010-present)
- [ ] Data completeness: >95% of matches have full statistics
- [ ] CSV files ready for ML pipeline ingestion
- [ ] Postgres database operational (optional)
- [ ] Daily incremental updates working
- [ ] Docker service running reliably
- [ ] Documentation complete
- [ ] Export utilities functional

---

## Implementation Status

### Completed Components

| Component | Location | Description |
|-----------|----------|-------------|
| Match Schemas | `app/schemas/matches/match.py` | Pydantic models for matches, maps, player stats |
| Match Services | `app/services/matches/` | Scrapers for results and match details |
| Match Endpoints | `app/api/endpoints/matches.py` | REST API for match data |
| Historical Scraper | `app/workers/scraper.py` | Batch scraper with resume capability |
| Incremental Scraper | `app/workers/incremental.py` | Updates with new matches only |
| CSV Storage | `app/storage/csv_storage.py` | CSV-based persistence |
| Docker Config | `docker-compose.yml` | Container orchestration |
| XPath Selectors | `app/utils/xpath.py` | Match data extraction patterns |

### API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/matches/results` | Paginated match results |
| GET | `/matches/{id}/details` | Full match details |
| GET | `/matches/{id}/maps` | Map results only |
| GET | `/matches/{id}/stats` | Player statistics only |
| POST | `/matches/scrape/historical` | Start historical scrape |
| GET | `/matches/scrape/status` | Check scrape progress |
| POST | `/matches/scrape/incremental` | Start incremental update |
| GET | `/matches/storage/stats` | Storage statistics |
| GET | `/matches/export/csv` | Get CSV file paths |

### Next Steps

1. **Run full historical scrape** with date range filters
2. **Test Docker deployment** with `docker-compose up`
3. **Implement Postgres storage** (optional, for production)
4. **Performance optimization** for large datasets

---

## Notes
- This plan focuses on **data collection only** - no ML feature engineering
- Data will be exported in clean CSV format for your existing ML pipeline
- Postgres is optional but recommended for production use
- Incremental updates ensure continuous data freshness
