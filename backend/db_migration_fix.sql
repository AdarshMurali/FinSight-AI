USE FinSight_AI;
SET NOCOUNT ON;

-- â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
-- STEP 1: Delete all tables child-first to respect FK constraints
-- â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
DELETE FROM Position_Changes_Log;
DELETE FROM Portfolio_Performance;
DELETE FROM Transactions;
DELETE FROM Positions;
DELETE FROM Portfolios;
DELETE FROM Customers;
DELETE FROM Market_Events;
DELETE FROM Securities;

DBCC CHECKIDENT ('Securities',            RESEED, 0) WITH NO_INFOMSGS;
DBCC CHECKIDENT ('Customers',             RESEED, 0) WITH NO_INFOMSGS;
DBCC CHECKIDENT ('Portfolios',            RESEED, 0) WITH NO_INFOMSGS;
DBCC CHECKIDENT ('Positions',             RESEED, 0) WITH NO_INFOMSGS;
DBCC CHECKIDENT ('Transactions',          RESEED, 0) WITH NO_INFOMSGS;
DBCC CHECKIDENT ('Portfolio_Performance', RESEED, 0) WITH NO_INFOMSGS;
DBCC CHECKIDENT ('Market_Events',         RESEED, 0) WITH NO_INFOMSGS;

-- ─────────────────────────────────────────────────────────────────────────────
-- STEP 2: 135 Securities (stocks, ETFs, commodities, currencies)
-- current_price is NOT NULL — included for every row
-- ─────────────────────────────────────────────────────────────────────────────
SET IDENTITY_INSERT Securities ON;
INSERT INTO Securities (security_id, ticker_symbol, security_name, security_type, sector, industry, country, exchange, currency, current_price, market_cap, created_at) VALUES
-- TECHNOLOGY (1-15)
( 1,'AAPL','Apple Inc',                    'stock','Technology',            'Consumer Electronics',    'United States','NASDAQ','USD', 195.50, 3020000.00,'2026-01-01'),
( 2,'MSFT','Microsoft Corporation',        'stock','Technology',            'Software',                'United States','NASDAQ','USD', 425.80, 3160000.00,'2026-01-01'),
( 3,'GOOGL','Alphabet Inc Class A',        'stock','Technology',            'Internet Services',       'United States','NASDAQ','USD', 178.40, 2180000.00,'2026-01-01'),
( 4,'AMZN','Amazon.com Inc',               'stock','Technology',            'E-Commerce & Cloud',      'United States','NASDAQ','USD', 195.20, 2050000.00,'2026-01-01'),
( 5,'NVDA','NVIDIA Corporation',           'stock','Technology',            'Semiconductors',          'United States','NASDAQ','USD', 875.40, 2150000.00,'2026-01-01'),
( 6,'META','Meta Platforms Inc',           'stock','Technology',            'Social Media',            'United States','NASDAQ','USD', 520.30, 1320000.00,'2026-01-01'),
( 7,'TSLA','Tesla Inc',                    'stock','Technology',            'Electric Vehicles',       'United States','NASDAQ','USD', 185.60,  592000.00,'2026-01-01'),
( 8,'AVGO','Broadcom Inc',                 'stock','Technology',            'Semiconductors',          'United States','NASDAQ','USD', 165.20,  775000.00,'2026-01-01'),
( 9,'ORCL','Oracle Corporation',           'stock','Technology',            'Software',                'United States','NYSE',  'USD', 152.30,  415000.00,'2026-01-01'),
(10,'ADBE','Adobe Inc',                    'stock','Technology',            'Software',                'United States','NASDAQ','USD', 445.70,  195000.00,'2026-01-01'),
(11,'CRM', 'Salesforce Inc',              'stock','Technology',            'Software',                'United States','NYSE',  'USD', 298.40,  290000.00,'2026-01-01'),
(12,'CSCO','Cisco Systems Inc',            'stock','Technology',            'Networking',              'United States','NASDAQ','USD',  56.80,  230000.00,'2026-01-01'),
(13,'AMD', 'Advanced Micro Devices',      'stock','Technology',            'Semiconductors',          'United States','NASDAQ','USD', 148.90,  242000.00,'2026-01-01'),
(14,'NFLX','Netflix Inc',                  'stock','Technology',            'Streaming',               'United States','NASDAQ','USD', 685.20,  295000.00,'2026-01-01'),
(15,'INTC','Intel Corporation',            'stock','Technology',            'Semiconductors',          'United States','NASDAQ','USD',  31.40,  133000.00,'2026-01-01'),
-- HEALTHCARE (16-30)
(16,'JNJ', 'Johnson & Johnson',           'stock','Healthcare',            'Pharmaceuticals',         'United States','NYSE',  'USD', 152.80,  367000.00,'2026-01-01'),
(17,'UNH', 'UnitedHealth Group',          'stock','Healthcare',            'Health Insurance',        'United States','NYSE',  'USD', 492.50,  458000.00,'2026-01-01'),
(18,'LLY', 'Eli Lilly and Company',       'stock','Healthcare',            'Pharmaceuticals',         'United States','NYSE',  'USD', 780.60,  742000.00,'2026-01-01'),
(19,'ABBV','AbbVie Inc',                   'stock','Healthcare',            'Pharmaceuticals',         'United States','NYSE',  'USD', 192.40,  340000.00,'2026-01-01'),
(20,'PFE', 'Pfizer Inc',                  'stock','Healthcare',            'Pharmaceuticals',         'United States','NYSE',  'USD',  27.80,  158000.00,'2026-01-01'),
(21,'MRK', 'Merck & Co',                  'stock','Healthcare',            'Pharmaceuticals',         'United States','NYSE',  'USD', 128.50,  326000.00,'2026-01-01'),
(22,'TMO', 'Thermo Fisher Scientific',    'stock','Healthcare',            'Life Sciences',           'United States','NYSE',  'USD', 562.80,  215000.00,'2026-01-01'),
(23,'ABT', 'Abbott Laboratories',         'stock','Healthcare',            'Medical Devices',         'United States','NYSE',  'USD', 122.40,  213000.00,'2026-01-01'),
(24,'DHR', 'Danaher Corporation',         'stock','Healthcare',            'Life Sciences',           'United States','NYSE',  'USD', 245.60,  178000.00,'2026-01-01'),
(25,'AMGN','Amgen Inc',                    'stock','Healthcare',            'Biotechnology',           'United States','NASDAQ','USD', 318.90,  171000.00,'2026-01-01'),
(26,'GILD','Gilead Sciences',              'stock','Healthcare',            'Biotechnology',           'United States','NASDAQ','USD',  92.30,  115000.00,'2026-01-01'),
(27,'REGN','Regeneron Pharmaceuticals',    'stock','Healthcare',            'Biotechnology',           'United States','NASDAQ','USD',1085.40,  118000.00,'2026-01-01'),
(28,'VRTX','Vertex Pharmaceuticals',       'stock','Healthcare',            'Biotechnology',           'United States','NASDAQ','USD', 482.60,  125000.00,'2026-01-01'),
(29,'ISRG','Intuitive Surgical',           'stock','Healthcare',            'Medical Devices',         'United States','NASDAQ','USD', 448.70,  160000.00,'2026-01-01'),
(30,'CVS', 'CVS Health Corporation',      'stock','Healthcare',            'Healthcare Services',     'United States','NYSE',  'USD',  58.40,   75000.00,'2026-01-01'),
-- FINANCIALS (31-45)
(31,'JPM', 'JPMorgan Chase & Co',         'stock','Financials',            'Banking',                 'United States','NYSE',  'USD', 228.50,  670000.00,'2026-01-01'),
(32,'BAC', 'Bank of America',             'stock','Financials',            'Banking',                 'United States','NYSE',  'USD',  44.20,  346000.00,'2026-01-01'),
(33,'WFC', 'Wells Fargo & Company',       'stock','Financials',            'Banking',                 'United States','NYSE',  'USD',  62.80,  232000.00,'2026-01-01'),
(34,'GS',  'Goldman Sachs Group',         'stock','Financials',            'Investment Banking',      'United States','NYSE',  'USD', 512.40,  174000.00,'2026-01-01'),
(35,'MS',  'Morgan Stanley',              'stock','Financials',            'Investment Banking',      'United States','NYSE',  'USD', 125.60,  218000.00,'2026-01-01'),
(36,'BLK', 'BlackRock Inc',               'stock','Financials',            'Asset Management',        'United States','NYSE',  'USD', 978.30,  148000.00,'2026-01-01'),
(37,'V',   'Visa Inc',                    'stock','Financials',            'Payment Processing',      'United States','NYSE',  'USD', 312.80,  672000.00,'2026-01-01'),
(38,'MA',  'Mastercard Inc',              'stock','Financials',            'Payment Processing',      'United States','NYSE',  'USD', 498.60,  478000.00,'2026-01-01'),
(39,'AXP', 'American Express',            'stock','Financials',            'Credit Services',         'United States','NYSE',  'USD', 265.40,  192000.00,'2026-01-01'),
(40,'SCHW','Charles Schwab Corp',          'stock','Financials',            'Brokerage',               'United States','NYSE',  'USD',  82.30,  150000.00,'2026-01-01'),
(41,'C',   'Citigroup Inc',               'stock','Financials',            'Banking',                 'United States','NYSE',  'USD',  72.40,  142000.00,'2026-01-01'),
(42,'COF', 'Capital One Financial',       'stock','Financials',            'Credit Services',         'United States','NYSE',  'USD', 168.90,   68000.00,'2026-01-01'),
(43,'CME', 'CME Group Inc',               'stock','Financials',            'Exchanges',               'United States','NASDAQ','USD', 238.50,   86000.00,'2026-01-01'),
(44,'SPGI','S&P Global Inc',               'stock','Financials',            'Financial Data',          'United States','NYSE',  'USD', 485.20,  160000.00,'2026-01-01'),
(45,'ICE', 'Intercontinental Exchange',   'stock','Financials',            'Exchanges',               'United States','NYSE',  'USD', 165.80,   95000.00,'2026-01-01'),
-- ENERGY (46-55)
(46,'XOM', 'Exxon Mobil Corporation',     'stock','Energy',                'Oil & Gas',               'United States','NYSE',  'USD', 112.60,  461000.00,'2026-01-01'),
(47,'CVX', 'Chevron Corporation',         'stock','Energy',                'Oil & Gas',               'United States','NYSE',  'USD', 158.20,  301000.00,'2026-01-01'),
(48,'COP', 'ConocoPhillips',              'stock','Energy',                'Oil & Gas',               'United States','NYSE',  'USD', 115.40,  148000.00,'2026-01-01'),
(49,'SLB', 'Schlumberger NV',             'stock','Energy',                'Oilfield Services',       'United States','NYSE',  'USD',  48.70,   69000.00,'2026-01-01'),
(50,'EOG', 'EOG Resources',               'stock','Energy',                'Oil & Gas',               'United States','NYSE',  'USD', 128.90,   75000.00,'2026-01-01'),
(51,'MPC', 'Marathon Petroleum',          'stock','Energy',                'Refining',                'United States','NYSE',  'USD', 185.40,   78000.00,'2026-01-01'),
(52,'OXY', 'Occidental Petroleum',        'stock','Energy',                'Oil & Gas',               'United States','NYSE',  'USD',  58.30,   53000.00,'2026-01-01'),
(53,'HAL', 'Halliburton Company',         'stock','Energy',                'Oilfield Services',       'United States','NYSE',  'USD',  35.80,   32000.00,'2026-01-01'),
(54,'DVN', 'Devon Energy',                'stock','Energy',                'Oil & Gas',               'United States','NYSE',  'USD',  44.20,   28000.00,'2026-01-01'),
(55,'KMI', 'Kinder Morgan Inc',           'stock','Energy',                'Pipelines',               'United States','NYSE',  'USD',  24.60,   55000.00,'2026-01-01'),
-- CONSUMER DISCRETIONARY (56-65)
(56,'HD',  'Home Depot Inc',              'stock','Consumer Discretionary','Home Improvement',        'United States','NYSE',  'USD', 398.50,  408000.00,'2026-01-01'),
(57,'MCD', 'McDonalds Corporation',       'stock','Consumer Discretionary','Restaurants',             'United States','NYSE',  'USD', 312.80,  226000.00,'2026-01-01'),
(58,'NKE', 'Nike Inc',                    'stock','Consumer Discretionary','Apparel',                 'United States','NYSE',  'USD',  78.60,  119000.00,'2026-01-01'),
(59,'SBUX','Starbucks Corporation',        'stock','Consumer Discretionary','Restaurants',             'United States','NASDAQ','USD',  82.40,   93000.00,'2026-01-01'),
(60,'TGT', 'Target Corporation',          'stock','Consumer Discretionary','Retail',                  'United States','NYSE',  'USD', 148.60,   69000.00,'2026-01-01'),
(61,'LOW', 'Lowes Companies',             'stock','Consumer Discretionary','Home Improvement',        'United States','NYSE',  'USD', 258.40,  150000.00,'2026-01-01'),
(62,'COST','Costco Wholesale',             'stock','Consumer Discretionary','Retail',                  'United States','NASDAQ','USD', 895.60,  396000.00,'2026-01-01'),
(63,'GM',  'General Motors',              'stock','Consumer Discretionary','Automotive',              'United States','NYSE',  'USD',  52.30,   60000.00,'2026-01-01'),
(64,'F',   'Ford Motor Company',          'stock','Consumer Discretionary','Automotive',              'United States','NYSE',  'USD',  11.40,   45000.00,'2026-01-01'),
(65,'ABNB','Airbnb Inc',                   'stock','Consumer Discretionary','Travel Tech',             'United States','NASDAQ','USD', 148.20,   95000.00,'2026-01-01'),
-- CONSUMER STAPLES (66-73)
(66,'WMT', 'Walmart Inc',                 'stock','Consumer Staples',      'Retail',                  'United States','NYSE',  'USD',  82.40,  220000.00,'2026-01-01'),
(67,'PG',  'Procter & Gamble',            'stock','Consumer Staples',      'Consumer Goods',          'United States','NYSE',  'USD', 172.80,  405000.00,'2026-01-01'),
(68,'KO',  'Coca-Cola Company',           'stock','Consumer Staples',      'Beverages',               'United States','NYSE',  'USD',  65.40,  282000.00,'2026-01-01'),
(69,'PEP', 'PepsiCo Inc',                 'stock','Consumer Staples',      'Beverages',               'United States','NASDAQ','USD', 162.50,  224000.00,'2026-01-01'),
(70,'CL',  'Colgate-Palmolive',           'stock','Consumer Staples',      'Consumer Goods',          'United States','NYSE',  'USD',  98.20,   82000.00,'2026-01-01'),
(71,'DIS', 'Walt Disney Company',         'stock','Consumer Staples',      'Entertainment',           'United States','NYSE',  'USD', 118.40,  216000.00,'2026-01-01'),
(72,'CMCSA','Comcast Corporation',         'stock','Consumer Staples',      'Media',                   'United States','NASDAQ','USD',  44.80,  185000.00,'2026-01-01'),
(73,'VZ',  'Verizon Communications',      'stock','Consumer Staples',      'Telecommunications',      'United States','NYSE',  'USD',  44.20,  186000.00,'2026-01-01'),
-- INDUSTRIALS (74-83)
(74,'BA',  'Boeing Company',              'stock','Industrials',            'Aerospace',               'United States','NYSE',  'USD', 192.50,  118000.00,'2026-01-01'),
(75,'RTX', 'Raytheon Technologies',       'stock','Industrials',            'Aerospace & Defense',     'United States','NYSE',  'USD', 118.60,  174000.00,'2026-01-01'),
(76,'HON', 'Honeywell International',     'stock','Industrials',            'Conglomerate',            'United States','NASDAQ','USD', 228.40,  149000.00,'2026-01-01'),
(77,'CAT', 'Caterpillar Inc',             'stock','Industrials',            'Machinery',               'United States','NYSE',  'USD', 385.20,  203000.00,'2026-01-01'),
(78,'DE',  'Deere & Company',             'stock','Industrials',            'Machinery',               'United States','NYSE',  'USD', 392.80,  109000.00,'2026-01-01'),
(79,'LMT', 'Lockheed Martin',             'stock','Industrials',            'Aerospace & Defense',     'United States','NYSE',  'USD', 512.60,  131000.00,'2026-01-01'),
(80,'GE',  'General Electric',            'stock','Industrials',            'Aerospace',               'United States','NYSE',  'USD', 185.40,  203000.00,'2026-01-01'),
(81,'UPS', 'United Parcel Service',       'stock','Industrials',            'Logistics',               'United States','NYSE',  'USD', 128.60,  109000.00,'2026-01-01'),
(82,'NOC', 'Northrop Grumman',            'stock','Industrials',            'Aerospace & Defense',     'United States','NYSE',  'USD', 498.20,   75000.00,'2026-01-01'),
(83,'FDX', 'FedEx Corporation',           'stock','Industrials',            'Logistics',               'United States','NYSE',  'USD', 298.40,   75000.00,'2026-01-01'),
-- REAL ESTATE (84-88)
(84,'PLD', 'Prologis Inc',                'stock','Real Estate',            'Industrial REIT',         'United States','NYSE',  'USD', 112.40,   98000.00,'2026-01-01'),
(85,'AMT', 'American Tower Corp',         'stock','Real Estate',            'Cell Tower REIT',         'United States','NYSE',  'USD', 188.60,   89000.00,'2026-01-01'),
(86,'EQIX','Equinix Inc',                  'stock','Real Estate',            'Data Center REIT',        'United States','NASDAQ','USD', 848.20,   76000.00,'2026-01-01'),
(87,'CCI', 'Crown Castle Inc',            'stock','Real Estate',            'Cell Tower REIT',         'United States','NYSE',  'USD',  98.40,   42000.00,'2026-01-01'),
(88,'SPG', 'Simon Property Group',        'stock','Real Estate',            'Retail REIT',             'United States','NYSE',  'USD', 142.80,   44000.00,'2026-01-01'),
-- UTILITIES (89-93)
(89,'NEE', 'NextEra Energy',              'stock','Utilities',              'Electric Utilities',      'United States','NYSE',  'USD',  68.50,  139000.00,'2026-01-01'),
(90,'DUK', 'Duke Energy Corporation',     'stock','Utilities',              'Electric Utilities',      'United States','NYSE',  'USD', 112.80,   87000.00,'2026-01-01'),
(91,'SO',  'Southern Company',            'stock','Utilities',              'Electric Utilities',      'United States','NYSE',  'USD',  88.40,   95000.00,'2026-01-01'),
(92,'AEP', 'American Electric Power',     'stock','Utilities',              'Electric Utilities',      'United States','NYSE',  'USD',  98.60,   52000.00,'2026-01-01'),
(93,'EXC', 'Exelon Corporation',          'stock','Utilities',              'Electric Utilities',      'United States','NYSE',  'USD',  42.80,   42000.00,'2026-01-01'),
-- MATERIALS (94-98)
(94,'LIN', 'Linde plc',                   'stock','Materials',              'Industrial Gases',        'Ireland',       'NYSE',  'USD', 448.60,  215000.00,'2026-01-01'),
(95,'APD', 'Air Products and Chemicals',  'stock','Materials',              'Industrial Gases',        'United States', 'NYSE', 'USD', 268.40,   60000.00,'2026-01-01'),
(96,'SHW', 'Sherwin-Williams',            'stock','Materials',              'Paints & Coatings',       'United States','NYSE',  'USD', 348.60,   90000.00,'2026-01-01'),
(97,'FCX', 'Freeport-McMoRan',            'stock','Materials',              'Copper Mining',           'United States','NYSE',  'USD',  48.20,   69000.00,'2026-01-01'),
(98,'NEM', 'Newmont Corporation',         'stock','Materials',              'Gold Mining',             'United States','NYSE',  'USD',  42.80,   54000.00,'2026-01-01'),
-- INTERNATIONAL (99-105)
( 99,'TSM', 'Taiwan Semiconductor Mfg',  'stock','Technology',            'Semiconductors',          'Taiwan',        'NYSE',  'USD', 165.40,  856000.00,'2026-01-01'),
(100,'SHOP','Shopify Inc',                 'stock','Technology',            'E-Commerce',              'Canada',        'NYSE',  'USD',  82.40,  104000.00,'2026-01-01'),
(101,'SPOT','Spotify Technology SA',       'stock','Technology',            'Streaming',               'Sweden',        'NYSE',  'USD', 358.60,   70000.00,'2026-01-01'),
(102,'UBER','Uber Technologies',           'stock','Technology',            'Ridesharing',             'United States','NYSE',  'USD',  78.40,  156000.00,'2026-01-01'),
(103,'ASML','ASML Holding NV',             'stock','Technology',            'Semiconductor Equipment', 'Netherlands',  'NASDAQ','USD', 885.20,  355000.00,'2026-01-01'),
(104,'NVO', 'Novo Nordisk A/S',            'stock','Healthcare',            'Pharmaceuticals',         'Denmark',       'NYSE',  'USD', 112.60,  512000.00,'2026-01-01'),
(105,'SAP', 'SAP SE',                     'stock','Technology',            'Software',                'Germany',       'NYSE',  'USD', 248.40,  298000.00,'2026-01-01'),
-- ETFs (106-125)
(106,'SPY', 'SPDR S&P 500 ETF Trust',                  'etf','Diversified',    'Index Fund',           'United States','NYSE',  'USD', 568.40, 520000.00,'2026-01-01'),
(107,'QQQ', 'Invesco QQQ Trust',                       'etf','Technology',     'Index Fund',           'United States','NASDAQ','USD', 498.60, 265000.00,'2026-01-01'),
(108,'IWM', 'iShares Russell 2000 ETF',                'etf','Diversified',    'Small Cap',            'United States','NYSE',  'USD', 208.40,  77000.00,'2026-01-01'),
(109,'VTI', 'Vanguard Total Stock Market ETF',         'etf','Diversified',    'Total Market',         'United States','NYSE',  'USD', 278.60, 392000.00,'2026-01-01'),
(110,'EFA', 'iShares MSCI EAFE ETF',                   'etf','International',  'Developed Markets',    'United States','NYSE',  'USD',  85.40,  97000.00,'2026-01-01'),
(111,'EEM', 'iShares MSCI Emerging Markets ETF',       'etf','International',  'Emerging Markets',     'United States','NYSE',  'USD',  44.20,  33000.00,'2026-01-01'),
(112,'XLK', 'Technology Select Sector SPDR',           'etf','Technology',     'Sector ETF',           'United States','NYSE',  'USD', 228.80,  68000.00,'2026-01-01'),
(113,'XLF', 'Financial Select Sector SPDR',            'etf','Financials',     'Sector ETF',           'United States','NYSE',  'USD',  44.80,  49000.00,'2026-01-01'),
(114,'XLE', 'Energy Select Sector SPDR',               'etf','Energy',         'Sector ETF',           'United States','NYSE',  'USD',  98.60,  39000.00,'2026-01-01'),
(115,'XLV', 'Health Care Select Sector SPDR',          'etf','Healthcare',     'Sector ETF',           'United States','NYSE',  'USD', 168.40,  43000.00,'2026-01-01'),
(116,'XLI', 'Industrial Select Sector SPDR',           'etf','Industrials',    'Sector ETF',           'United States','NYSE',  'USD', 132.80,  23000.00,'2026-01-01'),
(117,'XLP', 'Consumer Staples Select Sector SPDR',     'etf','Consumer Staples','Sector ETF',          'United States','NYSE',  'USD',  82.60,  19000.00,'2026-01-01'),
(118,'XLY', 'Consumer Discretionary Select SPDR',      'etf','Consumer Discretionary','Sector ETF',    'United States','NYSE',  'USD', 195.80,  22000.00,'2026-01-01'),
(119,'AGG', 'iShares Core US Aggregate Bond ETF',      'etf','Fixed Income',   'Bond ETF',             'United States','NYSE',  'USD',  98.40, 118000.00,'2026-01-01'),
(120,'TLT', 'iShares 20+ Year Treasury Bond ETF',      'etf','Fixed Income',   'Government Bond ETF',  'United States','NASDAQ','USD',  88.60,  53000.00,'2026-01-01'),
(121,'HYG', 'iShares iBoxx High Yield Corp Bond ETF',  'etf','Fixed Income',   'High Yield Bond ETF',  'United States','NYSE',  'USD',  78.80,  23000.00,'2026-01-01'),
(122,'LQD', 'iShares iBoxx IG Corporate Bond ETF',     'etf','Fixed Income',   'IG Bond ETF',          'United States','NYSE',  'USD', 112.40,  39000.00,'2026-01-01'),
(123,'GLD', 'SPDR Gold Shares',                        'etf','Commodities',    'Gold ETF',             'United States','NYSE',  'USD', 228.40,  74000.00,'2026-01-01'),
(124,'VNQ', 'Vanguard Real Estate ETF',                'etf','Real Estate',    'REIT ETF',             'United States','NYSE',  'USD',  92.60,  43000.00,'2026-01-01'),
(125,'BND', 'Vanguard Total Bond Market ETF',          'etf','Fixed Income',   'Bond ETF',             'United States','NASDAQ','USD',  74.80,  97000.00,'2026-01-01'),
-- COMMODITIES & CURRENCIES (126-135)
(126,'GC=F',     'Gold Futures',        'commodity','Commodities','Precious Metals','United States','COMEX','USD',2485.50,NULL,'2026-01-01'),
(127,'SI=F',     'Silver Futures',      'commodity','Commodities','Precious Metals','United States','COMEX','USD',  32.45,NULL,'2026-01-01'),
(128,'CL=F',     'Crude Oil WTI Futures','commodity','Commodities','Energy',        'United States','NYMEX','USD',  78.50,NULL,'2026-01-01'),
(129,'NG=F',     'Natural Gas Futures', 'commodity','Commodities','Energy',        'United States','NYMEX','USD',   3.25,NULL,'2026-01-01'),
(130,'ZC=F',     'Corn Futures',        'commodity','Commodities','Agriculture',   'United States','CBOT', 'USD', 478.50,NULL,'2026-01-01'),
(131,'ZW=F',     'Wheat Futures',       'commodity','Commodities','Agriculture',   'United States','CBOT', 'USD', 592.75,NULL,'2026-01-01'),
(132,'EURUSD=X', 'EUR/USD',             'currency', 'Currencies', 'Forex',         'Global',       'FOREX','USD',   1.0925,NULL,'2026-01-01'),
(133,'GBPUSD=X', 'GBP/USD',             'currency', 'Currencies', 'Forex',         'Global',       'FOREX','USD',   1.2845,NULL,'2026-01-01'),
(134,'USDJPY=X', 'USD/JPY',             'currency', 'Currencies', 'Forex',         'Global',       'FOREX','USD', 148.50,NULL,'2026-01-01'),
(135,'USDCAD=X', 'USD/CAD',             'currency', 'Currencies', 'Forex',         'Global',       'FOREX','USD',   1.3525,NULL,'2026-01-01');
SET IDENTITY_INSERT Securities OFF;

-- â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
-- STEP 2: 20 Customers
-- institution_type: asset_manager | hedge_fund | sovereign_wealth | pension_fund | family_office
-- risk_profile:     conservative | moderate | aggressive | very_aggressive
-- â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
SET IDENTITY_INSERT Customers ON;
INSERT INTO Customers (customer_id, customer_name, institution_type, aum, risk_profile, country, contact_email, created_at) VALUES
( 1, 'BlackRock Institutional Trust',        'asset_manager',   10000000000000.00, 'moderate',        'United States',       'institutional@blackrock.com',   '2019-01-02'),
( 2, 'Vanguard Group',                       'asset_manager',    8000000000000.00, 'conservative',    'United States',       'institutional@vanguard.com',    '2019-01-02'),
( 3, 'State Street Global Advisors',         'asset_manager',    4100000000000.00, 'moderate',        'United States',       'institutional@ssga.com',        '2019-01-02'),
( 4, 'Fidelity Investments',                 'asset_manager',    4500000000000.00, 'moderate',        'United States',       'institutional@fidelity.com',    '2019-01-02'),
( 5, 'PIMCO',                                'asset_manager',    2000000000000.00, 'conservative',    'United States',       'institutional@pimco.com',       '2019-01-02'),
( 6, 'Goldman Sachs Asset Management',       'asset_manager',    2800000000000.00, 'aggressive',      'United States',       'institutional@gsam.com',        '2019-01-02'),
( 7, 'J.P. Morgan Asset Management',         'asset_manager',    3200000000000.00, 'moderate',        'United States',       'institutional@jpmam.com',       '2019-01-02'),
( 8, 'Morgan Stanley Investment Management', 'asset_manager',    1500000000000.00, 'aggressive',      'United States',       'institutional@msim.com',        '2019-01-02'),
( 9, 'T. Rowe Price',                        'asset_manager',    1600000000000.00, 'moderate',        'United States',       'institutional@troweprice.com',  '2019-01-02'),
(10, 'Wellington Management',                'asset_manager',    1100000000000.00, 'moderate',        'United States',       'institutional@wellington.com',  '2019-01-02'),
(11, 'Bridgewater Associates',               'hedge_fund',        150000000000.00, 'very_aggressive', 'United States',       'investor.relations@bwater.com', '2019-01-02'),
(12, 'Renaissance Technologies',             'hedge_fund',        130000000000.00, 'very_aggressive', 'United States',       'ir@rentec.com',                 '2019-01-02'),
(13, 'Citadel',                              'hedge_fund',         62000000000.00, 'very_aggressive', 'United States',       'ir@citadel.com',                '2019-01-02'),
(14, 'Two Sigma',                            'hedge_fund',         60000000000.00, 'aggressive',      'United States',       'ir@twosigma.com',               '2019-01-02'),
(15, 'AQR Capital Management',               'hedge_fund',        120000000000.00, 'aggressive',      'United States',       'ir@aqr.com',                    '2019-01-02'),
(16, 'Norway Government Pension Fund Global','sovereign_wealth', 1700000000000.00, 'moderate',        'Norway',              'contact@nbim.no',               '2019-01-02'),
(17, 'Abu Dhabi Investment Authority',       'sovereign_wealth',  993000000000.00, 'moderate',        'United Arab Emirates','contact@adia.ae',               '2019-01-02'),
(18, 'CalPERS',                              'pension_fund',      503000000000.00, 'conservative',    'United States',       'contact@calpers.ca.gov',        '2019-01-02'),
(19, 'Ontario Teachers Pension Plan',        'pension_fund',      249000000000.00, 'moderate',        'Canada',              'contact@otpp.com',              '2019-01-02'),
(20, 'Rockefeller Family Office',            'family_office',      10000000000.00, 'conservative',    'United States',       'office@rockefeller.com',        '2019-01-02');
SET IDENTITY_INSERT Customers OFF;

-- â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
-- STEP 3: 50 Portfolios
-- strategy_type: balanced | growth | value | quantitative | global_macro | event_driven | market_neutral | long_short
-- â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
SET IDENTITY_INSERT Portfolios ON;
INSERT INTO Portfolios (portfolio_id, customer_id, portfolio_name, total_value, cash_balance, currency, inception_date, strategy_type, benchmark) VALUES
-- BlackRock (cust 1)
( 1,  1, 'BLK Core Equity Portfolio',           2500000000.00,  200000000.00, 'USD', '2019-01-02', 'balanced',      'S&P 500'),
( 2,  1, 'BLK Smart Beta Factor',                850000000.00,   50000000.00, 'USD', '2020-03-15', 'quantitative',  'MSCI World Factor'),
( 3,  1, 'BLK Global Macro Opportunities',      1200000000.00,  120000000.00, 'USD', '2018-06-01', 'global_macro',  'MSCI ACWI'),
-- Vanguard (cust 2)
( 4,  2, 'VG Total Market Index',               5000000000.00,   50000000.00, 'USD', '2010-01-04', 'quantitative',  'CRSP US Total Market'),
( 5,  2, 'VG Dividend Appreciation',            1800000000.00,   90000000.00, 'USD', '2015-05-01', 'value',         'Nasdaq US Dividend Achievers'),
( 6,  2, 'VG Core Bond Portfolio',              2200000000.00,  110000000.00, 'USD', '2012-08-15', 'balanced',      'Bloomberg US Aggregate'),
-- State Street (cust 3)
( 7,  3, 'SSGA S&P 500 Growth',                 1500000000.00,   75000000.00, 'USD', '2017-03-01', 'growth',        'S&P 500 Growth'),
( 8,  3, 'SSGA International Equity',            600000000.00,   60000000.00, 'USD', '2018-09-01', 'global_macro',  'MSCI EAFE'),
-- Fidelity (cust 4)
( 9,  4, 'Fidelity Growth Company',              900000000.00,   45000000.00, 'USD', '2016-07-01', 'growth',        'Russell 1000 Growth'),
(10,  4, 'Fidelity Balanced',                   1100000000.00,  110000000.00, 'USD', '2014-01-02', 'balanced',      '60/40 Blend'),
(11,  4, 'Fidelity Select Healthcare',           400000000.00,   20000000.00, 'USD', '2019-11-01', 'growth',        'MSCI Health Care'),
-- PIMCO (cust 5)
(12,  5, 'PIMCO Total Return',                  3500000000.00,  350000000.00, 'USD', '2008-01-02', 'balanced',      'Bloomberg US Aggregate'),
(13,  5, 'PIMCO Investment Grade Corporate',    2800000000.00,  140000000.00, 'USD', '2010-06-01', 'balanced',      'Bloomberg IG Corporate'),
-- Goldman Sachs AM (cust 6)
(14,  6, 'GS Equity Opportunities',              700000000.00,   70000000.00, 'USD', '2020-01-15', 'growth',        'S&P 500'),
(15,  6, 'GS Tactical Multi-Asset',              500000000.00,  100000000.00, 'USD', '2021-03-01', 'event_driven',  '60/40 Blend'),
-- JPM AM (cust 7)
(16,  7, 'JPM U.S. Equity Growth',              1300000000.00,   65000000.00, 'USD', '2017-01-03', 'growth',        'Russell 1000 Growth'),
(17,  7, 'JPM Core Bond',                       2100000000.00,  105000000.00, 'USD', '2015-08-01', 'balanced',      'Bloomberg US Aggregate'),
(18,  7, 'JPM Emerging Markets Equity',          800000000.00,   80000000.00, 'USD', '2019-02-01', 'global_macro',  'MSCI EM'),
-- Morgan Stanley IM (cust 8)
(19,  8, 'MS Global Franchise',                 1400000000.00,   70000000.00, 'USD', '2018-04-02', 'growth',        'MSCI World'),
(20,  8, 'MS Equity Long/Short',                 600000000.00,  120000000.00, 'USD', '2020-07-01', 'long_short',    'HFRX Equity Hedge'),
-- T. Rowe Price (cust 9)
(21,  9, 'TRP Capital Appreciation',            1100000000.00,   55000000.00, 'USD', '2016-01-04', 'growth',        'S&P 500'),
(22,  9, 'TRP Equity Income',                    700000000.00,   35000000.00, 'USD', '2017-06-01', 'value',         'Russell 1000 Value'),
-- Wellington (cust 10)
(23, 10, 'Wellington Quality Growth',           1600000000.00,   80000000.00, 'USD', '2016-09-01', 'growth',        'MSCI World'),
(24, 10, 'Wellington Strategic Value',           900000000.00,   45000000.00, 'USD', '2018-03-01', 'value',         'Russell 1000 Value'),
(25, 10, 'Wellington Commodities & Rates',      1200000000.00,  120000000.00, 'USD', '2019-06-03', 'global_macro',  'Bloomberg Commodity'),
-- Bridgewater (cust 11)
(26, 11, 'Bridgewater All Weather',            15000000000.00,  750000000.00, 'USD', '2000-01-03', 'balanced',      'CPI+5%'),
(27, 11, 'Bridgewater Pure Alpha',              8000000000.00,  800000000.00, 'USD', '2001-07-02', 'market_neutral','LIBOR+5%'),
-- Renaissance (cust 12)
(28, 12, 'Renaissance Institutional Equities',  5000000000.00,  250000000.00, 'USD', '2005-01-03', 'quantitative',  'Russell 1000'),
(29, 12, 'Renaissance Macro Strategy',          3000000000.00,  300000000.00, 'USD', '2008-06-02', 'global_macro',  'MSCI ACWI'),
-- Citadel (cust 13)
(30, 13, 'Citadel Global Equities',             8000000000.00, 1600000000.00, 'USD', '2002-01-07', 'long_short',    'HFRX Equity'),
(31, 13, 'Citadel Fixed Income Strategies',     5000000000.00,  500000000.00, 'USD', '2003-04-01', 'balanced',      'Bloomberg Aggregate'),
-- Two Sigma (cust 14)
(32, 14, 'Two Sigma Equity Factor',             4000000000.00,  200000000.00, 'USD', '2012-01-03', 'quantitative',  'Russell 3000'),
(33, 14, 'Two Sigma Event Driven',              2000000000.00,  400000000.00, 'USD', '2015-06-01', 'event_driven',  'HFRX Event Driven'),
-- AQR (cust 15)
(34, 15, 'AQR Momentum Strategy',               6000000000.00,  300000000.00, 'USD', '2009-01-02', 'quantitative',  'MSCI World Momentum'),
(35, 15, 'AQR Risk Parity',                     4000000000.00,  400000000.00, 'USD', '2011-03-01', 'market_neutral','CPI+5%'),
-- Norway GPFG (cust 16)
(36, 16, 'GPFG Global Equity',               800000000000.00,40000000000.00, 'NOK', '1998-01-02', 'growth',        'FTSE Global All Cap'),
(37, 16, 'GPFG Fixed Income',               270000000000.00,13500000000.00, 'NOK', '1998-01-02', 'balanced',      'Bloomberg Global Aggregate'),
(38, 16, 'GPFG Real Estate',                 30000000000.00, 1500000000.00, 'NOK', '2010-01-04', 'value',         'MSCI Global Real Estate'),
-- ADIA (cust 17)
(39, 17, 'ADIA Global Diversified',          350000000000.00,35000000000.00, 'AED', '1976-01-05', 'balanced',      '60/40 Global'),
(40, 17, 'ADIA Emerging Markets Growth',     130000000000.00,13000000000.00, 'AED', '2005-06-01', 'global_macro',  'MSCI EM'),
-- CalPERS (cust 18)
(41, 18, 'CalPERS Global Equity',            280000000000.00,14000000000.00, 'USD', '1988-01-04', 'balanced',      'MSCI ACWI IMI'),
(42, 18, 'CalPERS Growth Equity',             50000000000.00, 2500000000.00, 'USD', '2000-07-03', 'growth',        'Russell 1000 Growth'),
(43, 18, 'CalPERS Core Fixed Income',         80000000000.00, 4000000000.00, 'USD', '1988-01-04', 'balanced',      'Bloomberg US Aggregate'),
-- Ontario Teachers (cust 19)
(44, 19, 'OTPP Public Equities',              80000000000.00, 4000000000.00, 'CAD', '1990-01-02', 'growth',        'MSCI World'),
(45, 19, 'OTPP Infrastructure',               40000000000.00, 2000000000.00, 'CAD', '1991-06-03', 'value',         'CPI+4%'),
(46, 19, 'OTPP Fixed Income',                 60000000000.00, 3000000000.00, 'CAD', '1990-01-02', 'balanced',      'Bloomberg Canada Aggregate'),
-- Rockefeller (cust 20)
(47, 20, 'Rockefeller ESG Leaders',            3000000000.00,  150000000.00, 'USD', '2019-01-07', 'growth',        'MSCI ESG Leaders'),
(48, 20, 'Rockefeller Dividend Growth',        2000000000.00,  100000000.00, 'USD', '2018-03-01', 'value',         'S&P Dividend Aristocrats'),
(49, 20, 'Rockefeller Market Neutral',          500000000.00,  100000000.00, 'USD', '2021-01-04', 'market_neutral','T-Bill+3%'),
(50, 20, 'Rockefeller Commodities',             300000000.00,   30000000.00, 'USD', '2022-06-01', 'global_macro',  'Bloomberg Commodity');
SET IDENTITY_INSERT Portfolios OFF;

-- â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
-- STEP 4: ~200 Positions
-- weight is decimal(5,4) â€” store as fraction: 0.2500 = 25%, NOT 25.00
-- security IDs: AAPL=1 MSFT=2 GOOGL=3 AMZN=4 NVDA=5 META=6 TSLA=7 AVGO=8
--   ORCL=9 ADBE=10 CRM=11 CSCO=12 AMD=13 NFLX=14 INTC=15
--   JNJ=16 UNH=17 LLY=18 ABBV=19 PFE=20 MRK=21 TMO=22 ABT=23 DHR=24 AMGN=25
--   GILD=26 REGN=27 VRTX=28 ISRG=29 CVS=30
--   JPM=31 BAC=32 WFC=33 GS=34 MS=35 BLK=36 V=37 MA=38 AXP=39 SCHW=40
--   C=41 COF=42 CME=43 SPGI=44 ICE=45
--   XOM=46 CVX=47 COP=48 SLB=49 EOG=50 MPC=51 OXY=52 HAL=53 DVN=54 KMI=55
--   HD=56 MCD=57 NKE=58 SBUX=59 TGT=60 LOW=61 COST=62 GM=63 F=64 ABNB=65
--   WMT=66 PG=67 KO=68 PEP=69 CL=70 DIS=71 CMCSA=72 VZ=73
--   BA=74 RTX=75 HON=76 CAT=77 DE=78 LMT=79 GE=80 UPS=81 NOC=82 FDX=83
--   PLD=84 AMT=85 EQIX=86 CCI=87 SPG=88 NEE=89 DUK=90 SO=91 AEP=92 EXC=93
--   LIN=94 APD=95 SHW=96 FCX=97 NEM=98
--   TSM=99 SHOP=100 SPOT=101 UBER=102 ASML=103 NVO=104 SAP=105
--   SPY=106 QQQ=107 IWM=108 VTI=109 EFA=110 EEM=111
--   XLK=112 XLF=113 XLE=114 XLV=115 XLI=116 XLP=117 XLY=118
--   AGG=119 TLT=120 HYG=121 LQD=122 GLD=123 VNQ=124 BND=125
--   GC=F=126 SI=F=127 CL=F=128 NG=F=129 ZC=F=130 ZW=F=131
--   EURUSD=X=132 GBPUSD=X=133 USDJPY=X=134 USDCAD=X=135
-- â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
SET IDENTITY_INSERT Positions ON;
INSERT INTO Positions (position_id, portfolio_id, security_id, quantity, avg_cost_basis, current_price, market_value, weight, position_type, opened_date) VALUES
-- P1: BLK Core Equity (balanced)
(  1,  1, 106, 1200000.0000,  545.0000,  560.0000,  672000000.00, 0.2688, 'long', '2019-03-01'),
(  2,  1, 107,  500000.0000,  470.0000,  490.0000,  245000000.00, 0.0980, 'long', '2019-03-01'),
(  3,  1, 109, 1500000.0000,  265.0000,  280.0000,  420000000.00, 0.1680, 'long', '2019-04-01'),
(  4,  1, 119, 3000000.0000,   94.0000,   97.0000,  291000000.00, 0.1164, 'long', '2019-04-01'),
(  5,  1, 123,  800000.0000,  215.0000,  230.0000,  184000000.00, 0.0736, 'long', '2020-01-02'),
-- P2: BLK Smart Beta Factor (quantitative)
(  6,  2,   1, 400000.0000,  155.0000,  195.0000,   78000000.00, 0.0918, 'long', '2020-04-01'),
(  7,  2,   2, 180000.0000,  300.0000,  420.0000,   75600000.00, 0.0889, 'long', '2020-04-01'),
(  8,  2,  37, 270000.0000,  220.0000,  285.0000,   76950000.00, 0.0906, 'long', '2020-04-01'),
(  9,  2,  31, 330000.0000,  160.0000,  225.0000,   74250000.00, 0.0873, 'long', '2020-04-01'),
( 10,  2, 112, 330000.0000,  190.0000,  235.0000,   77550000.00, 0.0912, 'long', '2020-05-01'),
-- P3: BLK Global Macro Opportunities (global_macro)
( 11,  3, 110, 2000000.0000,   74.0000,   80.0000,  160000000.00, 0.1333, 'long', '2018-07-01'),
( 12,  3, 111, 3000000.0000,   39.0000,   43.0000,  129000000.00, 0.1075, 'long', '2018-07-01'),
( 13,  3,  99,  700000.0000,  120.0000,  195.0000,  136500000.00, 0.1138, 'long', '2019-01-02'),
( 14,  3, 123,  500000.0000,  180.0000,  230.0000,  115000000.00, 0.0958, 'long', '2018-07-01'),
( 15,  3, 103,  130000.0000,  650.0000,  830.0000,  107900000.00, 0.0899, 'long', '2021-01-04'),
-- P4: VG Total Market Index (quantitative)
( 16,  4, 109,15000000.0000,  210.0000,  280.0000, 4200000000.00, 0.8400, 'long', '2010-02-01'),
( 17,  4, 125, 4000000.0000,   68.0000,   74.0000,  296000000.00, 0.0592, 'long', '2010-02-01'),
( 18,  4, 110, 5000000.0000,   55.0000,   80.0000,  400000000.00, 0.0800, 'long', '2010-02-01'),
-- P5: VG Dividend Appreciation (value)
( 19,  5,  16, 800000.0000,  120.0000,  150.0000,  120000000.00, 0.0667, 'long', '2015-06-01'),
( 20,  5,  67, 900000.0000,  130.0000,  170.0000,  153000000.00, 0.0850, 'long', '2015-06-01'),
( 21,  5,  68,2000000.0000,   50.0000,   65.0000,  130000000.00, 0.0722, 'long', '2015-06-01'),
( 22,  5,  73,3000000.0000,   38.0000,   40.0000,  120000000.00, 0.0667, 'long', '2015-06-01'),
( 23,  5,  66,1200000.0000,   70.0000,   90.0000,  108000000.00, 0.0600, 'long', '2015-07-01'),
-- P6: VG Core Bond Portfolio (balanced)
( 24,  6, 119, 8000000.0000,   94.0000,   97.0000,  776000000.00, 0.3527, 'long', '2012-09-01'),
( 25,  6, 125,10000000.0000,   68.0000,   74.0000,  740000000.00, 0.3364, 'long', '2012-09-01'),
( 26,  6, 120, 3000000.0000,   95.0000,   93.0000,  279000000.00, 0.1268, 'long', '2012-09-01'),
( 27,  6, 122, 2500000.0000,  108.0000,  110.0000,  275000000.00, 0.1250, 'long', '2013-01-02'),
-- P7: SSGA S&P 500 Growth (growth)
( 28,  7, 106, 1200000.0000,  420.0000,  560.0000,  672000000.00, 0.4480, 'long', '2017-04-01'),
( 29,  7, 107,  500000.0000,  350.0000,  490.0000,  245000000.00, 0.1633, 'long', '2017-04-01'),
( 30,  7,   1, 1500000.0000,  120.0000,  195.0000,  292500000.00, 0.1950, 'long', '2017-04-01'),
( 31,  7,   5, 1000000.0000,   55.0000,  130.0000,  130000000.00, 0.0867, 'long', '2019-01-02'),
-- P8: SSGA International Equity (global_macro)
( 32,  8, 110, 3000000.0000,   62.0000,   80.0000,  240000000.00, 0.4000, 'long', '2018-10-01'),
( 33,  8, 111, 2000000.0000,   37.0000,   43.0000,   86000000.00, 0.1433, 'long', '2018-10-01'),
( 34,  8, 103,  100000.0000,  680.0000,  830.0000,   83000000.00, 0.1383, 'long', '2020-01-02'),
( 35,  8, 104, 1000000.0000,   85.0000,  115.0000,  115000000.00, 0.1917, 'long', '2020-06-01'),
-- P9: Fidelity Growth Company (growth)
( 36,  9,   1, 800000.0000,  140.0000,  195.0000,  156000000.00, 0.1733, 'long', '2016-08-01'),
( 37,  9,   2, 350000.0000,  280.0000,  420.0000,  147000000.00, 0.1633, 'long', '2016-08-01'),
( 38,  9,   3, 700000.0000,  120.0000,  175.0000,  122500000.00, 0.1361, 'long', '2016-08-01'),
( 39,  9,   5, 900000.0000,   48.0000,  130.0000,  117000000.00, 0.1300, 'long', '2019-02-01'),
( 40,  9,   6, 250000.0000,  300.0000,  520.0000,  130000000.00, 0.1444, 'long', '2020-01-02'),
-- P10: Fidelity Balanced (balanced)
( 41, 10, 106,  700000.0000,  380.0000,  560.0000,  392000000.00, 0.3564, 'long', '2014-02-01'),
( 42, 10, 119, 3000000.0000,   93.0000,   97.0000,  291000000.00, 0.2645, 'long', '2014-02-01'),
( 43, 10,  31, 350000.0000,  140.0000,  225.0000,   78750000.00, 0.0716, 'long', '2014-02-01'),
( 44, 10,  16, 400000.0000,  110.0000,  150.0000,   60000000.00, 0.0545, 'long', '2014-02-01'),
-- P11: Fidelity Select Healthcare (growth)
( 45, 11,  17, 150000.0000,  380.0000,  510.0000,   76500000.00, 0.1913, 'long', '2019-12-01'),
( 46, 11,  18,  80000.0000,  600.0000,  870.0000,   69600000.00, 0.1740, 'long', '2020-06-01'),
( 47, 11,  22, 110000.0000,  450.0000,  600.0000,   66000000.00, 0.1650, 'long', '2019-12-01'),
( 48, 11,  23, 600000.0000,   82.0000,  105.0000,   63000000.00, 0.1575, 'long', '2019-12-01'),
( 49, 11, 115, 600000.0000,  120.0000,  145.0000,   87000000.00, 0.2175, 'long', '2019-12-01'),
-- P12: PIMCO Total Return (balanced)
( 50, 12, 119,12000000.0000,   93.0000,   97.0000, 1164000000.00, 0.3326, 'long', '2008-02-01'),
( 51, 12, 122, 8000000.0000,  105.0000,  110.0000,  880000000.00, 0.2514, 'long', '2008-02-01'),
( 52, 12, 125,10000000.0000,   67.0000,   74.0000,  740000000.00, 0.2114, 'long', '2008-02-01'),
( 53, 12, 121, 3000000.0000,   74.0000,   76.0000,  228000000.00, 0.0651, 'long', '2010-01-04'),
-- P13: PIMCO Investment Grade Corporate (balanced)
( 54, 13, 122,12000000.0000,  105.0000,  110.0000, 1320000000.00, 0.4714, 'long', '2010-07-01'),
( 55, 13, 119, 8000000.0000,   93.0000,   97.0000,  776000000.00, 0.2771, 'long', '2010-07-01'),
( 56, 13, 125, 8000000.0000,   67.0000,   74.0000,  592000000.00, 0.2114, 'long', '2010-07-01'),
-- P14: GS Equity Opportunities (growth)
( 57, 14,   5, 900000.0000,   45.0000,  130.0000,  117000000.00, 0.1671, 'long', '2020-02-01'),
( 58, 14,   6, 200000.0000,  200.0000,  520.0000,  104000000.00, 0.1486, 'long', '2020-02-01'),
( 59, 14,   4, 450000.0000,  150.0000,  195.0000,   87750000.00, 0.1254, 'long', '2020-02-01'),
( 60, 14,   7, 300000.0000,  190.0000,  250.0000,   75000000.00, 0.1071, 'long', '2020-02-01'),
( 61, 14,   3, 500000.0000,  130.0000,  175.0000,   87500000.00, 0.1250, 'long', '2020-02-01'),
-- P15: GS Tactical Multi-Asset (event_driven)
( 62, 15, 106, 300000.0000,  480.0000,  560.0000,  168000000.00, 0.3360, 'long', '2021-04-01'),
( 63, 15, 123, 200000.0000,  190.0000,  230.0000,   46000000.00, 0.0920, 'long', '2021-04-01'),
( 64, 15, 120, 500000.0000,   93.0000,   93.0000,   46500000.00, 0.0930, 'long', '2021-04-01'),
( 65, 15,  73,1000000.0000,   44.0000,   40.0000,   40000000.00, 0.0800, 'long', '2021-04-01'),
( 66, 15, 114, 500000.0000,   85.0000,   95.0000,   47500000.00, 0.0950, 'long', '2021-04-01'),
-- P16: JPM U.S. Equity Growth (growth)
( 67, 16,   1, 900000.0000,  145.0000,  195.0000,  175500000.00, 0.1350, 'long', '2017-02-01'),
( 68, 16,   2, 380000.0000,  270.0000,  420.0000,  159600000.00, 0.1228, 'long', '2017-02-01'),
( 69, 16,   4, 750000.0000,  145.0000,  195.0000,  146250000.00, 0.1125, 'long', '2017-02-01'),
( 70, 16,   6, 230000.0000,  280.0000,  520.0000,  119600000.00, 0.0920, 'long', '2020-01-02'),
( 71, 16,   5,1100000.0000,   45.0000,  130.0000,  143000000.00, 0.1100, 'long', '2019-01-02'),
-- P17: JPM Core Bond (balanced)
( 72, 17, 119, 8000000.0000,   93.0000,   97.0000,  776000000.00, 0.3695, 'long', '2015-09-01'),
( 73, 17, 122, 5000000.0000,  105.0000,  110.0000,  550000000.00, 0.2619, 'long', '2015-09-01'),
( 74, 17, 125, 6000000.0000,   67.0000,   74.0000,  444000000.00, 0.2114, 'long', '2015-09-01'),
( 75, 17, 121, 2000000.0000,   74.0000,   76.0000,  152000000.00, 0.0724, 'long', '2016-01-04'),
-- P18: JPM Emerging Markets (global_macro)
( 76, 18, 111, 3000000.0000,   37.0000,   43.0000,  129000000.00, 0.1613, 'long', '2019-03-01'),
( 77, 18, 110, 2000000.0000,   63.0000,   80.0000,  160000000.00, 0.2000, 'long', '2019-03-01'),
( 78, 18,  99, 500000.0000,  110.0000,  195.0000,   97500000.00, 0.1219, 'long', '2019-03-01'),
( 79, 18, 104,1000000.0000,   80.0000,  115.0000,  115000000.00, 0.1438, 'long', '2020-06-01'),
( 80, 18, 100,1200000.0000,   60.0000,   95.0000,  114000000.00, 0.1425, 'long', '2021-01-04'),
-- P19: MS Global Franchise (growth)
( 81, 19,   2, 350000.0000,  250.0000,  420.0000,  147000000.00, 0.1050, 'long', '2018-05-01'),
( 82, 19,   5, 900000.0000,   45.0000,  130.0000,  117000000.00, 0.0836, 'long', '2019-01-02'),
( 83, 19,   1, 600000.0000,  140.0000,  195.0000,  117000000.00, 0.0836, 'long', '2018-05-01'),
( 84, 19, 103, 100000.0000,  640.0000,  830.0000,   83000000.00, 0.0593, 'long', '2020-01-02'),
( 85, 19,  99, 500000.0000,  110.0000,  195.0000,   97500000.00, 0.0696, 'long', '2020-01-02'),
-- P20: MS Equity Long/Short (long_short)
( 86, 20,   1, 300000.0000,  155.0000,  195.0000,   58500000.00, 0.0975, 'long',  '2020-08-01'),
( 87, 20,   3, 250000.0000,  130.0000,  175.0000,   43750000.00, 0.0729, 'long',  '2020-08-01'),
( 88, 20,  37, 200000.0000,  220.0000,  285.0000,   57000000.00, 0.0950, 'long',  '2020-08-01'),
( 89, 20,  34, -80000.0000,  540.0000,  540.0000,  -43200000.00,-0.0720, 'short', '2021-03-01'),
( 90, 20,  46,-200000.0000,  115.0000,  115.0000,  -23000000.00,-0.0383, 'short', '2021-03-01'),
-- P21: TRP Capital Appreciation (growth)
( 91, 21,   1, 700000.0000,  140.0000,  195.0000,  136500000.00, 0.1241, 'long', '2016-02-01'),
( 92, 21,   4, 600000.0000,  145.0000,  195.0000,  117000000.00, 0.1064, 'long', '2016-02-01'),
( 93, 21,   3, 600000.0000,  110.0000,  175.0000,  105000000.00, 0.0955, 'long', '2016-02-01'),
( 94, 21,  14, 110000.0000,  400.0000,  700.0000,   77000000.00, 0.0700, 'long', '2018-01-02'),
( 95, 21,   6, 150000.0000,  250.0000,  520.0000,   78000000.00, 0.0709, 'long', '2020-01-02'),
-- P22: TRP Equity Income (value)
( 96, 22,  32,2000000.0000,   32.0000,   42.0000,   84000000.00, 0.1200, 'long', '2017-07-01'),
( 97, 22,  46, 600000.0000,   85.0000,  115.0000,   69000000.00, 0.0986, 'long', '2017-07-01'),
( 98, 22,  68,1500000.0000,   49.0000,   65.0000,   97500000.00, 0.1393, 'long', '2017-07-01'),
( 99, 22,  67, 500000.0000,  130.0000,  170.0000,   85000000.00, 0.1214, 'long', '2017-07-01'),
(100, 22,  16, 400000.0000,  110.0000,  150.0000,   60000000.00, 0.0857, 'long', '2017-07-01'),
-- P23: Wellington Quality Growth (growth)
(101, 23,   2, 300000.0000,  280.0000,  420.0000,  126000000.00, 0.0788, 'long', '2016-10-01'),
(102, 23,  37, 450000.0000,  210.0000,  285.0000,  128250000.00, 0.0802, 'long', '2016-10-01'),
(103, 23,  17, 200000.0000,  360.0000,  510.0000,  102000000.00, 0.0638, 'long', '2016-10-01'),
(104, 23,  38, 200000.0000,  340.0000,  480.0000,   96000000.00, 0.0600, 'long', '2016-10-01'),
(105, 23,   1, 600000.0000,  135.0000,  195.0000,  117000000.00, 0.0731, 'long', '2016-10-01'),
-- P24: Wellington Strategic Value (value)
(106, 24,  16, 500000.0000,  115.0000,  150.0000,   75000000.00, 0.0833, 'long', '2018-04-01'),
(107, 24,  67, 400000.0000,  125.0000,  170.0000,   68000000.00, 0.0756, 'long', '2018-04-01'),
(108, 24,  57, 250000.0000,  220.0000,  285.0000,   71250000.00, 0.0792, 'long', '2018-04-01'),
(109, 24,  56, 180000.0000,  320.0000,  390.0000,   70200000.00, 0.0780, 'long', '2018-04-01'),
(110, 24,  66, 700000.0000,   70.0000,   90.0000,   63000000.00, 0.0700, 'long', '2018-04-01'),
-- P25: Wellington Commodities & Rates (global_macro)
(111, 25, 123, 500000.0000,  170.0000,  230.0000,  115000000.00, 0.0958, 'long', '2019-07-01'),
(112, 25, 126,  50000.0000, 1800.0000, 2400.0000,  120000000.00, 0.1000, 'long', '2019-07-01'),
(113, 25, 128, 300000.0000,   65.0000,   80.0000,   24000000.00, 0.0200, 'long', '2019-07-01'),
(114, 25, 114,1500000.0000,   75.0000,   95.0000,  142500000.00, 0.1188, 'long', '2019-07-01'),
(115, 25, 120,3000000.0000,   94.0000,   93.0000,  279000000.00, 0.2325, 'long', '2019-07-01'),
-- P26: Bridgewater All Weather (balanced)
(116, 26, 106,4000000.0000,  380.0000,  560.0000, 2240000000.00, 0.1493, 'long', '2000-02-01'),
(117, 26, 120,20000000.0000,  85.0000,   93.0000, 1860000000.00, 0.1240, 'long', '2000-02-01'),
(118, 26, 123,5000000.0000,  120.0000,  230.0000, 1150000000.00, 0.0767, 'long', '2000-02-01'),
(119, 26, 114,8000000.0000,   55.0000,   95.0000,  760000000.00, 0.0507, 'long', '2000-02-01'),
(120, 26, 119,30000000.0000,  80.0000,   97.0000, 2910000000.00, 0.1940, 'long', '2000-02-01'),
-- P27: Bridgewater Pure Alpha (market_neutral)
(121, 27, 106, 2000000.0000,  380.0000,  560.0000, 1120000000.00, 0.1400, 'long',  '2001-08-01'),
(122, 27, 120,10000000.0000,   85.0000,   93.0000,  930000000.00, 0.1163, 'long',  '2001-08-01'),
(123, 27, 123, 3000000.0000,  120.0000,  230.0000,  690000000.00, 0.0863, 'long',  '2001-08-01'),
(124, 27, 126,  30000.0000, 1200.0000, 2400.0000,   72000000.00, 0.0090, 'long',  '2001-08-01'),
(125, 27, 106,-1500000.0000,  450.0000,  560.0000, -840000000.00,-0.1050, 'short', '2022-01-03'),
-- P28: Renaissance Institutional Equities (quantitative)
(126, 28,   1,1000000.0000,  130.0000,  195.0000,  195000000.00, 0.0390, 'long', '2005-02-01'),
(127, 28,   2, 500000.0000,  250.0000,  420.0000,  210000000.00, 0.0420, 'long', '2005-02-01'),
(128, 28,   5,2000000.0000,   25.0000,  130.0000,  260000000.00, 0.0520, 'long', '2019-01-02'),
(129, 28, 106, 600000.0000,  380.0000,  560.0000,  336000000.00, 0.0672, 'long', '2005-02-01'),
(130, 28, 107, 400000.0000,  300.0000,  490.0000,  196000000.00, 0.0392, 'long', '2005-02-01'),
-- P29: Renaissance Macro Strategy (global_macro)
(131, 29, 110,3000000.0000,   55.0000,   80.0000,  240000000.00, 0.0800, 'long', '2008-07-01'),
(132, 29, 111,4000000.0000,   28.0000,   43.0000,  172000000.00, 0.0573, 'long', '2008-07-01'),
(133, 29, 123,1000000.0000,  100.0000,  230.0000,  230000000.00, 0.0767, 'long', '2008-07-01'),
(134, 29, 132,5000000.0000,    1.1500,    1.0800,    5400000.00, 0.0018, 'long', '2008-07-01'),
(135, 29, 120,5000000.0000,   85.0000,   93.0000,  465000000.00, 0.1550, 'long', '2008-07-01'),
-- P30: Citadel Global Equities (long_short)
(136, 30,   2, 800000.0000,  300.0000,  420.0000,  336000000.00, 0.0420, 'long',  '2002-02-01'),
(137, 30,   1,1500000.0000,  120.0000,  195.0000,  292500000.00, 0.0366, 'long',  '2002-02-01'),
(138, 30,  31, 800000.0000,  120.0000,  225.0000,  180000000.00, 0.0225, 'long',  '2002-02-01'),
(139, 30,  46,-1000000.0000, 100.0000,  115.0000, -115000000.00,-0.0144, 'short', '2022-06-01'),
(140, 30,  64,-5000000.0000,  12.0000,   12.0000,  -60000000.00,-0.0075, 'short', '2022-06-01'),
-- P31: Citadel Fixed Income Strategies (balanced)
(141, 31, 119,12000000.0000,  90.0000,   97.0000, 1164000000.00, 0.2328, 'long', '2003-05-01'),
(142, 31, 122, 8000000.0000, 105.0000,  110.0000,  880000000.00, 0.1760, 'long', '2003-05-01'),
(143, 31, 125,10000000.0000,  65.0000,   74.0000,  740000000.00, 0.1480, 'long', '2003-05-01'),
(144, 31, 121, 5000000.0000,  72.0000,   76.0000,  380000000.00, 0.0760, 'long', '2003-05-01'),
-- P32: Two Sigma Equity Factor (quantitative)
(145, 32, 106,2000000.0000,  380.0000,  560.0000, 1120000000.00, 0.2800, 'long', '2012-02-01'),
(146, 32, 107,1000000.0000,  300.0000,  490.0000,  490000000.00, 0.1225, 'long', '2012-02-01'),
(147, 32, 108,1500000.0000,  150.0000,  210.0000,  315000000.00, 0.0788, 'long', '2012-02-01'),
(148, 32, 109,3000000.0000,  200.0000,  280.0000,  840000000.00, 0.2100, 'long', '2012-02-01'),
-- P33: Two Sigma Event Driven (event_driven)
(149, 33,   1, 500000.0000,  155.0000,  195.0000,   97500000.00, 0.0488, 'long', '2015-07-01'),
(150, 33,   7, 400000.0000,  200.0000,  250.0000,  100000000.00, 0.0500, 'long', '2020-01-02'),
(151, 33,  14, 100000.0000,  550.0000,  700.0000,   70000000.00, 0.0350, 'long', '2018-01-02'),
(152, 33,   6, 120000.0000,  300.0000,  520.0000,   62400000.00, 0.0312, 'long', '2020-01-02'),
(153, 33,   4, 400000.0000,  150.0000,  195.0000,   78000000.00, 0.0390, 'long', '2015-07-01'),
-- P34: AQR Momentum Strategy (quantitative)
(154, 34,   5,3000000.0000,   30.0000,  130.0000,  390000000.00, 0.0650, 'long', '2009-02-01'),
(155, 34,   6, 500000.0000,  200.0000,  520.0000,  260000000.00, 0.0433, 'long', '2020-01-02'),
(156, 34,   1,1200000.0000,  130.0000,  195.0000,  234000000.00, 0.0390, 'long', '2009-02-01'),
(157, 34,   2, 500000.0000,  250.0000,  420.0000,  210000000.00, 0.0350, 'long', '2009-02-01'),
(158, 34, 107,1000000.0000,  300.0000,  490.0000,  490000000.00, 0.0817, 'long', '2009-02-01'),
-- P35: AQR Risk Parity (market_neutral)
(159, 35, 106,1500000.0000,  380.0000,  560.0000,  840000000.00, 0.2100, 'long', '2011-04-01'),
(160, 35, 120,8000000.0000,   85.0000,   93.0000,  744000000.00, 0.1860, 'long', '2011-04-01'),
(161, 35, 123,1500000.0000,  120.0000,  230.0000,  345000000.00, 0.0863, 'long', '2011-04-01'),
(162, 35, 126,  15000.0000, 1200.0000, 2400.0000,   36000000.00, 0.0090, 'long', '2011-04-01'),
(163, 35, 119,6000000.0000,   82.0000,   97.0000,  582000000.00, 0.1455, 'long', '2011-04-01'),
-- P36: GPFG Global Equity (growth)
(164, 36, 106,200000000.0000, 280.0000, 560.0000,112000000000.00,0.1400, 'long', '1998-02-02'),
(165, 36, 110,500000000.0000,  35.0000,  80.0000, 40000000000.00,0.0500, 'long', '1998-02-02'),
(166, 36,   1, 50000000.0000, 100.0000, 195.0000,  9750000000.00,0.0122, 'long', '1998-02-02'),
(167, 36,   2, 30000000.0000, 200.0000, 420.0000, 12600000000.00,0.0158, 'long', '1998-02-02'),
(168, 36, 111,400000000.0000,  18.0000,  43.0000, 17200000000.00,0.0215, 'long', '1998-02-02'),
-- P37: GPFG Fixed Income (balanced)
(169, 37, 119,800000000.0000,  80.0000,  97.0000, 77600000000.00,0.2874, 'long', '1998-02-02'),
(170, 37, 125,600000000.0000,  58.0000,  74.0000, 44400000000.00,0.1644, 'long', '1998-02-02'),
(171, 37, 122,400000000.0000, 100.0000, 110.0000, 44000000000.00,0.1630, 'long', '1998-02-02'),
(172, 37, 120,400000000.0000,  85.0000,  93.0000, 37200000000.00,0.1378, 'long', '1998-02-02'),
-- P38: GPFG Real Estate (value)
(173, 38,  84,10000000.0000,   80.0000, 120.0000,  1200000000.00,0.0400, 'long', '2010-02-01'),
(174, 38,  85, 5000000.0000,  180.0000, 215.0000,  1075000000.00,0.0358, 'long', '2010-02-01'),
(175, 38, 124,20000000.0000,   75.0000,  88.0000,  1760000000.00,0.0587, 'long', '2010-02-01'),
(176, 38,  88,10000000.0000,  120.0000, 165.0000,  1650000000.00,0.0550, 'long', '2010-02-01'),
-- P39: ADIA Global Diversified (balanced)
(177, 39, 106,100000000.0000, 280.0000, 560.0000, 56000000000.00,0.1600, 'long', '1976-02-02'),
(178, 39, 119,500000000.0000,  75.0000,  97.0000, 48500000000.00,0.1386, 'long', '1976-02-02'),
(179, 39, 110,400000000.0000,  35.0000,  80.0000, 32000000000.00,0.0914, 'long', '1976-02-02'),
(180, 39, 123, 50000000.0000, 120.0000, 230.0000, 11500000000.00,0.0329, 'long', '1990-01-02'),
-- P40: ADIA Emerging Markets Growth (global_macro)
(181, 40, 111,500000000.0000,  18.0000,  43.0000, 21500000000.00,0.1654, 'long', '2005-07-01'),
(182, 40, 110,300000000.0000,  35.0000,  80.0000, 24000000000.00,0.1846, 'long', '2005-07-01'),
(183, 40,  99, 50000000.0000, 100.0000, 195.0000,  9750000000.00,0.0750, 'long', '2010-01-04'),
(184, 40, 104, 80000000.0000,  70.0000, 115.0000,  9200000000.00,0.0708, 'long', '2015-01-02'),
-- P41: CalPERS Global Equity (balanced)
(185, 41, 106,100000000.0000, 200.0000, 560.0000, 56000000000.00,0.2000, 'long', '1988-02-01'),
(186, 41, 110,300000000.0000,  30.0000,  80.0000, 24000000000.00,0.0857, 'long', '1988-02-01'),
(187, 41, 119,500000000.0000,  70.0000,  97.0000, 48500000000.00,0.1732, 'long', '1988-02-01'),
(188, 41, 111,200000000.0000,  18.0000,  43.0000,  8600000000.00,0.0307, 'long', '1988-02-01'),
-- P42: CalPERS Growth Equity (growth)
(189, 42,   1,10000000.0000, 100.0000,  195.0000,  1950000000.00,0.0390, 'long', '2000-08-01'),
(190, 42,   2, 5000000.0000, 200.0000,  420.0000,  2100000000.00,0.0420, 'long', '2000-08-01'),
(191, 42,   5,15000000.0000,  25.0000,  130.0000,  1950000000.00,0.0390, 'long', '2019-01-02'),
(192, 42, 107, 8000000.0000, 300.0000,  490.0000,  3920000000.00,0.0784, 'long', '2000-08-01'),
-- P43: CalPERS Core Fixed Income (balanced)
(193, 43, 119,300000000.0000,  75.0000,  97.0000, 29100000000.00,0.3638, 'long', '1988-02-01'),
(194, 43, 122,200000000.0000, 100.0000, 110.0000, 22000000000.00,0.2750, 'long', '1988-02-01'),
(195, 43, 125,200000000.0000,  60.0000,  74.0000, 14800000000.00,0.1850, 'long', '1988-02-01'),
-- P44: OTPP Public Equities (growth)
(196, 44, 106, 50000000.0000, 200.0000, 560.0000, 28000000000.00,0.3500, 'long', '1990-02-01'),
(197, 44, 110,150000000.0000,  30.0000,  80.0000, 12000000000.00,0.1500, 'long', '1990-02-01'),
(198, 44,   2,  8000000.0000, 200.0000, 420.0000,  3360000000.00,0.0420, 'long', '1990-02-01'),
(199, 44,   1, 12000000.0000, 100.0000, 195.0000,  2340000000.00,0.0293, 'long', '1990-02-01'),
-- P45: OTPP Infrastructure (value)
(200, 45, 116, 80000000.0000, 100.0000, 136.0000, 10880000000.00,0.2720, 'long', '1991-07-01'),
(201, 45,  89, 60000000.0000,  50.0000,  75.0000,  4500000000.00,0.1125, 'long', '1991-07-01'),
(202, 45,  81, 20000000.0000,  80.0000, 130.0000,  2600000000.00,0.0650, 'long', '1991-07-01'),
(203, 45,  76, 20000000.0000, 160.0000, 230.0000,  4600000000.00,0.1150, 'long', '1991-07-01'),
-- P46: OTPP Fixed Income (balanced)
(204, 46, 119,200000000.0000,  70.0000,  97.0000, 19400000000.00,0.3233, 'long', '1990-02-01'),
(205, 46, 125,200000000.0000,  60.0000,  74.0000, 14800000000.00,0.2467, 'long', '1990-02-01'),
(206, 46, 122,100000000.0000, 100.0000, 110.0000, 11000000000.00,0.1833, 'long', '1990-02-01'),
-- P47: Rockefeller ESG Leaders (growth)
(207, 47,   2, 1500000.0000, 310.0000,  420.0000,  630000000.00, 0.2100, 'long', '2019-02-01'),
(208, 47,   1, 2000000.0000, 140.0000,  195.0000,  390000000.00, 0.1300, 'long', '2019-02-01'),
(209, 47,   5, 2000000.0000,  48.0000,  130.0000,  260000000.00, 0.0867, 'long', '2019-02-01'),
(210, 47,  37,  800000.0000, 220.0000,  285.0000,  228000000.00, 0.0760, 'long', '2019-02-01'),
(211, 47,  17,  300000.0000, 380.0000,  510.0000,  153000000.00, 0.0510, 'long', '2019-02-01'),
-- P48: Rockefeller Dividend Growth (value)
(212, 48,  16,  700000.0000, 120.0000,  150.0000,  105000000.00, 0.0525, 'long', '2018-04-01'),
(213, 48,  67,  600000.0000, 130.0000,  170.0000,  102000000.00, 0.0510, 'long', '2018-04-01'),
(214, 48,  68, 1500000.0000,  50.0000,   65.0000,   97500000.00, 0.0488, 'long', '2018-04-01'),
(215, 48,  57,  350000.0000, 220.0000,  285.0000,   99750000.00, 0.0499, 'long', '2018-04-01'),
(216, 48,  66, 1000000.0000,  70.0000,   90.0000,   90000000.00, 0.0450, 'long', '2018-04-01'),
-- P49: Rockefeller Market Neutral (market_neutral)
(217, 49, 106,  150000.0000, 480.0000,  560.0000,   84000000.00, 0.1680, 'long',  '2021-02-01'),
(218, 49, 119,  800000.0000,  94.0000,   97.0000,   77600000.00, 0.1552, 'long',  '2021-02-01'),
(219, 49, 123,  100000.0000, 190.0000,  230.0000,   23000000.00, 0.0460, 'long',  '2021-02-01'),
(220, 49, 106, -100000.0000, 530.0000,  560.0000,  -56000000.00,-0.1120, 'short', '2021-06-01'),
-- P50: Rockefeller Commodities (global_macro)
(221, 50, 123,  300000.0000, 180.0000,  230.0000,   69000000.00, 0.2300, 'long', '2022-07-01'),
(222, 50, 114,  500000.0000,  80.0000,   95.0000,   47500000.00, 0.1583, 'long', '2022-07-01'),
(223, 50, 126,    5000.0000,1800.0000, 2400.0000,   12000000.00, 0.0400, 'long', '2022-07-01'),
(224, 50, 128,  200000.0000,  65.0000,   80.0000,   16000000.00, 0.0533, 'long', '2022-07-01');
SET IDENTITY_INSERT Positions OFF;

-- â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
-- STEP 5: Transactions
-- transaction_type: 'buy' | 'sell' | 'dividend' | 'split' | 'deposit' | 'withdrawal'
-- total_amount: NOT NULL â€” quantity * price
-- â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
SET IDENTITY_INSERT Transactions ON;
INSERT INTO Transactions (transaction_id, portfolio_id, security_id, transaction_type, quantity, price, transaction_date, fees, total_amount, notes) VALUES
(  1,  1, 106, 'buy',      500000.0000, 480.0000, '2019-03-01',  50000.00,  240000000.00, 'Initial SPY allocation'),
(  2,  1, 119, 'buy',     2000000.0000,  94.0000, '2019-04-01',  20000.00,  188000000.00, 'Bond allocation build'),
(  3,  2,   1, 'buy',      300000.0000, 150.0000, '2020-04-15',   5000.00,   45000000.00, 'AAPL factor position'),
(  4,  2,  37, 'buy',      200000.0000, 215.0000, '2020-04-15',   4000.00,   43000000.00, 'Visa factor position'),
(  5,  3, 110, 'buy',     1500000.0000,  74.0000, '2018-07-02',  15000.00,  111000000.00, 'EFA international core'),
(  6,  3, 123, 'buy',      300000.0000, 180.0000, '2018-07-02',   3000.00,   54000000.00, 'Gold hedge initiation'),
(  7,  4, 109, 'buy',    10000000.0000, 210.0000, '2010-02-01', 100000.00, 2100000000.00, 'VTI index core'),
(  8,  4, 125, 'buy',     3000000.0000,  68.0000, '2010-02-01',  30000.00,  204000000.00, 'BND bond complement'),
(  9,  5,  67, 'buy',      700000.0000, 130.0000, '2015-06-01',   7000.00,   91000000.00, 'Procter & Gamble position'),
( 10,  5,  68, 'buy',     1500000.0000,  50.0000, '2015-06-01',   5000.00,   75000000.00, 'Coca-Cola dividend position'),
( 11,  6, 119, 'buy',     5000000.0000,  94.0000, '2012-09-01',  50000.00,  470000000.00, 'AGG core bond'),
( 12,  6, 125, 'buy',     7000000.0000,  68.0000, '2012-09-01',  70000.00,  476000000.00, 'BND long duration'),
( 13,  7, 106, 'buy',      800000.0000, 420.0000, '2017-04-01',  80000.00,  336000000.00, 'S&P 500 core'),
( 14,  7,   1, 'buy',     1000000.0000, 120.0000, '2017-04-01',  10000.00,  120000000.00, 'Apple growth position'),
( 15,  8, 110, 'buy',     2000000.0000,  62.0000, '2018-10-01',  20000.00,  124000000.00, 'International developed'),
( 16,  8, 104, 'buy',      700000.0000,  85.0000, '2020-06-01',   7000.00,   59500000.00, 'Novo Nordisk addition'),
( 17,  9,   2, 'buy',      250000.0000, 280.0000, '2016-08-01',  10000.00,   70000000.00, 'MSFT growth core'),
( 18,  9,   5, 'buy',      500000.0000,  48.0000, '2019-02-01',   2000.00,   24000000.00, 'NVDA AI addition'),
( 19, 10, 106, 'buy',      500000.0000, 380.0000, '2014-02-01',  50000.00,  190000000.00, 'SPY balanced core'),
( 20, 10, 119, 'buy',     2000000.0000,  93.0000, '2014-02-01',  20000.00,  186000000.00, 'AGG bond core'),
( 21, 11,  17, 'buy',      100000.0000, 380.0000, '2019-12-01',  10000.00,   38000000.00, 'UnitedHealth position'),
( 22, 11,  18, 'buy',       50000.0000, 600.0000, '2020-06-01',   5000.00,   30000000.00, 'Eli Lilly GLP-1 thesis'),
( 23, 12, 119, 'buy',     8000000.0000,  93.0000, '2008-02-01',  80000.00,  744000000.00, 'AGG total return core'),
( 24, 12, 122, 'buy',     5000000.0000, 105.0000, '2008-02-01',  50000.00,  525000000.00, 'LQD IG credit'),
( 25, 13, 122, 'buy',     8000000.0000, 105.0000, '2010-07-01',  80000.00,  840000000.00, 'LQD investment grade'),
( 26, 13, 119, 'buy',     5000000.0000,  93.0000, '2010-07-01',  50000.00,  465000000.00, 'AGG complement'),
( 27, 14,   5, 'buy',      700000.0000,  45.0000, '2020-02-01',   3000.00,   31500000.00, 'NVDA AI theme'),
( 28, 14,   6, 'buy',      150000.0000, 200.0000, '2020-02-01',   5000.00,   30000000.00, 'Meta social platform'),
( 29, 15, 106, 'buy',      200000.0000, 480.0000, '2021-04-01',  20000.00,   96000000.00, 'Tactical equity core'),
( 30, 15, 123, 'buy',      150000.0000, 190.0000, '2021-04-01',   1500.00,   28500000.00, 'Gold hedge'),
( 31, 16,   1, 'buy',      700000.0000, 145.0000, '2017-02-01',   7000.00,  101500000.00, 'AAPL growth position'),
( 32, 16,   2, 'buy',      300000.0000, 270.0000, '2017-02-01',   9000.00,   81000000.00, 'MSFT cloud thesis'),
( 33, 17, 119, 'buy',     5000000.0000,  93.0000, '2015-09-01',  50000.00,  465000000.00, 'Core bond ladder'),
( 34, 17, 122, 'buy',     3000000.0000, 105.0000, '2015-09-01',  30000.00,  315000000.00, 'Investment grade credit'),
( 35, 18, 111, 'buy',     2000000.0000,  37.0000, '2019-03-01',  20000.00,   74000000.00, 'EM broad exposure'),
( 36, 18,  99, 'buy',      400000.0000, 110.0000, '2019-03-01',   4000.00,   44000000.00, 'TSMC semiconductor'),
( 37, 19,   2, 'buy',      250000.0000, 250.0000, '2018-05-01',   7500.00,   62500000.00, 'MSFT franchise quality'),
( 38, 19, 103, 'buy',       70000.0000, 640.0000, '2020-01-02',   7000.00,   44800000.00, 'ASML lithography moat'),
( 39, 20,   1, 'buy',      250000.0000, 155.0000, '2020-08-01',   2500.00,   38750000.00, 'Long Apple quality'),
( 40, 20,  34, 'sell',      60000.0000, 540.0000, '2021-03-01',   6000.00,   32400000.00, 'Short Goldman macro hedge'),
( 41, 21,   1, 'buy',      600000.0000, 140.0000, '2016-02-01',   6000.00,   84000000.00, 'AAPL capital appreciation'),
( 42, 21,   4, 'buy',      500000.0000, 145.0000, '2016-02-01',   5000.00,   72500000.00, 'Amazon platform thesis'),
( 43, 22,  32, 'buy',     1500000.0000,  32.0000, '2017-07-01',   5000.00,   48000000.00, 'BofA value position'),
( 44, 22,  68, 'buy',     1000000.0000,  49.0000, '2017-07-01',   5000.00,   49000000.00, 'KO dividend value'),
( 45, 23,   2, 'buy',      200000.0000, 280.0000, '2016-10-01',   6000.00,   56000000.00, 'MSFT quality compounder'),
( 46, 23,  17, 'buy',      150000.0000, 360.0000, '2016-10-01',   5000.00,   54000000.00, 'UNH healthcare quality'),
( 47, 24,  16, 'buy',      400000.0000, 115.0000, '2018-04-01',   4000.00,   46000000.00, 'JNJ defensive value'),
( 48, 24,  57, 'buy',      200000.0000, 220.0000, '2018-04-01',   4000.00,   44000000.00, 'MCD compounding franchise'),
( 49, 25, 123, 'buy',      400000.0000, 170.0000, '2019-07-01',   4000.00,   68000000.00, 'Gold commodity exposure'),
( 50, 25, 114, 'buy',     1200000.0000,  75.0000, '2019-07-01',  12000.00,   90000000.00, 'Energy sector allocation'),
( 51, 26, 106, 'buy',     2000000.0000, 280.0000, '2000-03-01', 200000.00,  560000000.00, 'All Weather equity leg'),
( 52, 26, 120, 'buy',    15000000.0000,  85.0000, '2000-03-01', 150000.00, 1275000000.00, 'All Weather long-term bonds'),
( 53, 27, 120, 'buy',     8000000.0000,  85.0000, '2001-09-01',  80000.00,  680000000.00, 'Pure Alpha bond position'),
( 54, 27, 123, 'buy',     1500000.0000, 120.0000, '2001-09-01',  15000.00,  180000000.00, 'Pure Alpha gold hedge'),
( 55, 28,   1, 'buy',      800000.0000, 130.0000, '2005-02-01',   8000.00,  104000000.00, 'RIEF equity position'),
( 56, 28, 106, 'buy',      400000.0000, 280.0000, '2005-02-01',  40000.00,  112000000.00, 'RIEF index core'),
( 57, 29, 110, 'buy',     2000000.0000,  55.0000, '2008-07-01',  20000.00,  110000000.00, 'Macro international'),
( 58, 29, 123, 'buy',      700000.0000, 100.0000, '2008-07-01',   7000.00,   70000000.00, 'Gold macro hedge'),
( 59, 30,   2, 'buy',      600000.0000, 300.0000, '2002-02-01',  60000.00,  180000000.00, 'Long MSFT quality'),
( 60, 30,  46, 'sell',     700000.0000,  90.0000, '2022-06-01',   7000.00,   63000000.00, 'Short energy hedge'),
( 61, 31, 119, 'buy',     8000000.0000,  90.0000, '2003-05-01',  80000.00,  720000000.00, 'Fixed income core'),
( 62, 31, 122, 'buy',     5000000.0000, 105.0000, '2003-05-01',  50000.00,  525000000.00, 'IG credit ladder'),
( 63, 32, 106, 'buy',     1500000.0000, 280.0000, '2012-02-01', 150000.00,  420000000.00, 'Factor SPY core'),
( 64, 32, 109, 'buy',     2000000.0000, 160.0000, '2012-02-01',  20000.00,  320000000.00, 'VTI total market'),
( 65, 33,   7, 'buy',      300000.0000, 200.0000, '2020-01-02',   3000.00,   60000000.00, 'TSLA event catalyst'),
( 66, 33,  14, 'buy',       80000.0000, 550.0000, '2018-01-02',   4000.00,   44000000.00, 'Netflix subscriber growth'),
( 67, 34,   5, 'buy',     2000000.0000,  30.0000, '2009-02-01',   2000.00,   60000000.00, 'NVDA momentum signal'),
( 68, 34, 107, 'buy',      700000.0000, 300.0000, '2009-02-01',  70000.00,  210000000.00, 'QQQ momentum index'),
( 69, 35, 106, 'buy',     1000000.0000, 280.0000, '2011-04-01', 100000.00,  280000000.00, 'Risk parity equity'),
( 70, 35, 120, 'buy',     5000000.0000,  85.0000, '2011-04-01',  50000.00,  425000000.00, 'Risk parity bonds'),
( 71, 36, 106, 'buy',   100000000.0000, 280.0000, '1998-03-02',5000000.00,28000000000.00, 'GPFG equity anchor'),
( 72, 36, 110, 'buy',   300000000.0000,  35.0000, '1998-03-02',3000000.00,10500000000.00, 'GPFG international'),
( 73, 37, 119, 'buy',   500000000.0000,  80.0000, '1998-03-02',5000000.00,40000000000.00, 'GPFG AGG bond core'),
( 74, 37, 125, 'buy',   400000000.0000,  58.0000, '1998-03-02',4000000.00,23200000000.00, 'GPFG BND complement'),
( 75, 38,  84, 'buy',     8000000.0000,  80.0000, '2010-02-01',  80000.00,  640000000.00, 'GPFG RE â€” Prologis'),
( 76, 38, 124, 'buy',    15000000.0000,  75.0000, '2010-02-01', 150000.00, 1125000000.00, 'GPFG RE â€” VNQ'),
( 77, 39, 106, 'buy',    80000000.0000, 200.0000, '1976-03-01',5000000.00,16000000000.00, 'ADIA global equity'),
( 78, 39, 119, 'buy',   300000000.0000,  75.0000, '1976-03-01',3000000.00,22500000000.00, 'ADIA fixed income'),
( 79, 40, 111, 'buy',   300000000.0000,  18.0000, '2005-07-01',3000000.00, 5400000000.00, 'ADIA EM broad'),
( 80, 40,  99, 'buy',    40000000.0000, 100.0000, '2010-01-04', 400000.00, 4000000000.00, 'ADIA TSMC semiconductor'),
( 81, 41, 106, 'buy',    70000000.0000, 200.0000, '1988-03-01',5000000.00,14000000000.00, 'CalPERS equity anchor'),
( 82, 41, 119, 'buy',   350000000.0000,  70.0000, '1988-03-01',3500000.00,24500000000.00, 'CalPERS bond anchor'),
( 83, 42,   1, 'buy',     8000000.0000, 100.0000, '2000-08-01',  80000.00,  800000000.00, 'CalPERS AAPL growth'),
( 84, 42,   5, 'buy',    10000000.0000,  25.0000, '2019-01-02',  25000.00,  250000000.00, 'CalPERS NVDA AI addition'),
( 85, 43, 119, 'buy',   200000000.0000,  75.0000, '1988-03-01',2000000.00,15000000000.00, 'CalPERS fixed income AGG'),
( 86, 43, 122, 'buy',   150000000.0000, 100.0000, '1988-03-01',1500000.00,15000000000.00, 'CalPERS IG credit LQD'),
( 87, 44, 106, 'buy',    40000000.0000, 200.0000, '1990-03-01',2000000.00, 8000000000.00, 'OTPP SPY equity'),
( 88, 44, 110, 'buy',   100000000.0000,  30.0000, '1990-03-01',1000000.00, 3000000000.00, 'OTPP EFA international'),
( 89, 45, 116, 'buy',    60000000.0000, 100.0000, '1991-07-01', 600000.00, 6000000000.00, 'OTPP XLI infrastructure'),
( 90, 45,  89, 'buy',    50000000.0000,  50.0000, '1991-07-01', 500000.00, 2500000000.00, 'OTPP NEE utilities'),
( 91, 46, 119, 'buy',   150000000.0000,  70.0000, '1990-03-01',1500000.00,10500000000.00, 'OTPP fixed income AGG'),
( 92, 46, 125, 'buy',   150000000.0000,  60.0000, '1990-03-01',1500000.00, 9000000000.00, 'OTPP BND complement'),
( 93, 47,   2, 'buy',     1200000.0000, 310.0000, '2019-02-01',  36000.00,  372000000.00, 'Rockefeller ESG MSFT'),
( 94, 47,   1, 'buy',     1500000.0000, 140.0000, '2019-02-01',  15000.00,  210000000.00, 'Rockefeller ESG AAPL'),
( 95, 48,  16, 'buy',      600000.0000, 120.0000, '2018-04-01',   6000.00,   72000000.00, 'Rockefeller JNJ dividend'),
( 96, 48,  68, 'buy',     1200000.0000,  50.0000, '2018-04-01',   6000.00,   60000000.00, 'Rockefeller KO dividend'),
( 97, 49, 106, 'buy',      120000.0000, 480.0000, '2021-02-01',  12000.00,   57600000.00, 'Market neutral long SPY'),
( 98, 49, 106, 'sell',      80000.0000, 530.0000, '2021-06-01',   8000.00,   42400000.00, 'Market neutral short overlay'),
( 99, 50, 123, 'buy',      250000.0000, 180.0000, '2022-07-01',   2500.00,   45000000.00, 'Commodities gold leg'),
(100, 50, 114, 'buy',      400000.0000,  80.0000, '2022-07-01',   4000.00,   32000000.00, 'Commodities energy ETF');
SET IDENTITY_INSERT Transactions OFF;

-- â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
-- STEP 6: Portfolio_Performance â€” 3 dates per portfolio (150 rows)
-- â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
SET IDENTITY_INSERT Portfolio_Performance ON;
INSERT INTO Portfolio_Performance (performance_id, portfolio_id, as_of_date, total_value, daily_return, mtd_return, ytd_return, volatility, sharpe_ratio, max_drawdown, alpha, beta) VALUES
-- P1 BLK Core Equity
(  1,  1, '2024-12-31', 2200000000.00, 0.0042, 0.0320, 0.1180, 0.1220, 0.9800, -0.0850, 0.0120, 0.9800),
(  2,  1, '2025-06-30', 2380000000.00, 0.0018, 0.0150, 0.0820, 0.1190, 1.0200, -0.0620, 0.0130, 0.9900),
(  3,  1, '2025-12-31', 2500000000.00, 0.0031, 0.0290, 0.1340, 0.1240, 1.0500, -0.0780, 0.0140, 0.9700),
-- P2 BLK Smart Beta
(  4,  2, '2024-12-31',  820000000.00, 0.0055, 0.0380, 0.1520, 0.1450, 1.1200, -0.1020, 0.0380, 1.0100),
(  5,  2, '2025-06-30',  834000000.00, 0.0022, 0.0180, 0.0890, 0.1430, 1.0900, -0.0720, 0.0340, 1.0000),
(  6,  2, '2025-12-31',  850000000.00, 0.0041, 0.0310, 0.1650, 0.1480, 1.1500, -0.0980, 0.0420, 1.0200),
-- P3 BLK Global Macro
(  7,  3, '2024-12-31', 1100000000.00, 0.0033, 0.0250, 0.0920, 0.1380, 0.7800, -0.1120, 0.0250, 0.8200),
(  8,  3, '2025-06-30', 1155000000.00, 0.0015, 0.0120, 0.0650, 0.1350, 0.8100, -0.0880, 0.0220, 0.8400),
(  9,  3, '2025-12-31', 1200000000.00, 0.0028, 0.0220, 0.0980, 0.1360, 0.8500, -0.1050, 0.0280, 0.8300),
-- P4 VG Total Market
( 10,  4, '2024-12-31', 4650000000.00, 0.0048, 0.0350, 0.1290, 0.1350, 0.9500, -0.0920, 0.0020, 0.9980),
( 11,  4, '2025-06-30', 4820000000.00, 0.0021, 0.0160, 0.0780, 0.1320, 0.9600, -0.0680, 0.0010, 0.9990),
( 12,  4, '2025-12-31', 5000000000.00, 0.0039, 0.0300, 0.1350, 0.1340, 0.9700, -0.0890, 0.0015, 0.9990),
-- P5 VG Dividend
( 13,  5, '2024-12-31', 1720000000.00, 0.0028, 0.0210, 0.0820, 0.0980, 0.8900, -0.0720, 0.0180, 0.8200),
( 14,  5, '2025-06-30', 1762000000.00, 0.0012, 0.0090, 0.0480, 0.0950, 0.9100, -0.0510, 0.0160, 0.8300),
( 15,  5, '2025-12-31', 1800000000.00, 0.0025, 0.0200, 0.0880, 0.0960, 0.9300, -0.0690, 0.0190, 0.8100),
-- P6 VG Core Bond
( 16,  6, '2024-12-31', 2090000000.00,-0.0012, 0.0050,-0.0280, 0.0650, 0.3800, -0.1250,-0.0050, 0.9500),
( 17,  6, '2025-06-30', 2145000000.00, 0.0008, 0.0040, 0.0180, 0.0620, 0.4200, -0.0980,-0.0020, 0.9600),
( 18,  6, '2025-12-31', 2200000000.00,-0.0005, 0.0060,-0.0120, 0.0640, 0.4000, -0.1150,-0.0030, 0.9500),
-- P7 SSGA S&P 500 Growth
( 19,  7, '2024-12-31', 1380000000.00, 0.0062, 0.0420, 0.1780, 0.1680, 1.1800, -0.1120, 0.0520, 1.0800),
( 20,  7, '2025-06-30', 1441000000.00, 0.0028, 0.0210, 0.1020, 0.1650, 1.2100, -0.0830, 0.0480, 1.0900),
( 21,  7, '2025-12-31', 1500000000.00, 0.0055, 0.0380, 0.1920, 0.1700, 1.2500, -0.1050, 0.0550, 1.0800),
-- P8 SSGA International
( 22,  8, '2024-12-31',  560000000.00, 0.0028, 0.0190, 0.0680, 0.1420, 0.6500, -0.1320, 0.0150, 0.9200),
( 23,  8, '2025-06-30',  580000000.00, 0.0013, 0.0100, 0.0420, 0.1390, 0.6800, -0.1010, 0.0130, 0.9300),
( 24,  8, '2025-12-31',  600000000.00, 0.0025, 0.0180, 0.0750, 0.1410, 0.6900, -0.1240, 0.0160, 0.9200),
-- P9 Fidelity Growth
( 25,  9, '2024-12-31',  840000000.00, 0.0075, 0.0520, 0.2150, 0.1920, 1.2800, -0.1350, 0.0620, 1.1500),
( 26,  9, '2025-06-30',  871000000.00, 0.0035, 0.0260, 0.1250, 0.1880, 1.3100, -0.1010, 0.0580, 1.1600),
( 27,  9, '2025-12-31',  900000000.00, 0.0068, 0.0480, 0.2280, 0.1950, 1.3400, -0.1280, 0.0660, 1.1400),
-- P10 Fidelity Balanced
( 28, 10, '2024-12-31', 1040000000.00, 0.0038, 0.0280, 0.1050, 0.1050, 0.9200, -0.0920, 0.0150, 0.9200),
( 29, 10, '2025-06-30', 1068000000.00, 0.0018, 0.0130, 0.0620, 0.1020, 0.9500, -0.0680, 0.0130, 0.9300),
( 30, 10, '2025-12-31', 1100000000.00, 0.0035, 0.0260, 0.1120, 0.1040, 0.9800, -0.0880, 0.0160, 0.9200),
-- P11 Fidelity Healthcare
( 31, 11, '2024-12-31',  375000000.00, 0.0048, 0.0340, 0.1320, 0.1580, 1.0200, -0.1180, 0.0480, 0.8900),
( 32, 11, '2025-06-30',  388000000.00, 0.0022, 0.0160, 0.0780, 0.1550, 1.0500, -0.0890, 0.0430, 0.9000),
( 33, 11, '2025-12-31',  400000000.00, 0.0043, 0.0310, 0.1420, 0.1560, 1.0800, -0.1120, 0.0510, 0.8800),
-- P12 PIMCO Total Return
( 34, 12, '2024-12-31', 3300000000.00,-0.0008, 0.0060,-0.0120, 0.0580, 0.4500, -0.1050, 0.0080, 0.9200),
( 35, 12, '2025-06-30', 3405000000.00, 0.0005, 0.0030, 0.0150, 0.0550, 0.4800, -0.0820, 0.0090, 0.9300),
( 36, 12, '2025-12-31', 3500000000.00,-0.0003, 0.0070,-0.0050, 0.0560, 0.4600, -0.0980, 0.0085, 0.9200),
-- P13 PIMCO IG Corp
( 37, 13, '2024-12-31', 2650000000.00,-0.0005, 0.0080,-0.0050, 0.0520, 0.5200, -0.0950, 0.0120, 0.8800),
( 38, 13, '2025-06-30', 2723000000.00, 0.0006, 0.0040, 0.0180, 0.0500, 0.5500, -0.0730, 0.0130, 0.8900),
( 39, 13, '2025-12-31', 2800000000.00,-0.0002, 0.0090, 0.0050, 0.0510, 0.5300, -0.0900, 0.0125, 0.8800),
-- P14 GS Equity Opps
( 40, 14, '2024-12-31',  650000000.00, 0.0082, 0.0580, 0.2480, 0.2150, 1.3800, -0.1580, 0.0720, 1.2200),
( 41, 14, '2025-06-30',  674000000.00, 0.0038, 0.0290, 0.1420, 0.2100, 1.4100, -0.1180, 0.0680, 1.2300),
( 42, 14, '2025-12-31',  700000000.00, 0.0075, 0.0530, 0.2620, 0.2180, 1.4500, -0.1480, 0.0760, 1.2100),
-- P15 GS Tactical
( 43, 15, '2024-12-31',  475000000.00, 0.0032, 0.0240, 0.0920, 0.1280, 0.8200, -0.1080, 0.0250, 0.8800),
( 44, 15, '2025-06-30',  488000000.00, 0.0015, 0.0110, 0.0540, 0.1250, 0.8500, -0.0800, 0.0220, 0.8900),
( 45, 15, '2025-12-31',  500000000.00, 0.0029, 0.0210, 0.0980, 0.1260, 0.8800, -0.1020, 0.0260, 0.8800),
-- P16 JPM US Growth
( 46, 16, '2024-12-31', 1220000000.00, 0.0068, 0.0480, 0.1980, 0.1820, 1.2400, -0.1280, 0.0560, 1.1200),
( 47, 16, '2025-06-30', 1262000000.00, 0.0032, 0.0240, 0.1140, 0.1780, 1.2700, -0.0960, 0.0520, 1.1300),
( 48, 16, '2025-12-31', 1300000000.00, 0.0062, 0.0440, 0.2100, 0.1850, 1.3000, -0.1200, 0.0590, 1.1200),
-- P17 JPM Core Bond
( 49, 17, '2024-12-31', 1990000000.00,-0.0010, 0.0055,-0.0220, 0.0600, 0.4100, -0.1100,-0.0030, 0.9400),
( 50, 17, '2025-06-30', 2047000000.00, 0.0006, 0.0035, 0.0160, 0.0580, 0.4400, -0.0860,-0.0010, 0.9500),
( 51, 17, '2025-12-31', 2100000000.00,-0.0007, 0.0065,-0.0100, 0.0590, 0.4200, -0.1050,-0.0020, 0.9400),
-- P18 JPM EM
( 52, 18, '2024-12-31',  755000000.00, 0.0035, 0.0260, 0.0880, 0.1850, 0.5800, -0.1650, 0.0280, 0.9800),
( 53, 18, '2025-06-30',  778000000.00, 0.0016, 0.0120, 0.0520, 0.1820, 0.6100, -0.1260, 0.0250, 0.9900),
( 54, 18, '2025-12-31',  800000000.00, 0.0032, 0.0240, 0.0940, 0.1830, 0.6400, -0.1580, 0.0300, 0.9800),
-- P19 MS Global Franchise
( 55, 19, '2024-12-31', 1320000000.00, 0.0060, 0.0420, 0.1760, 0.1580, 1.2100, -0.1220, 0.0520, 1.0200),
( 56, 19, '2025-06-30', 1361000000.00, 0.0028, 0.0210, 0.1020, 0.1550, 1.2400, -0.0920, 0.0480, 1.0300),
( 57, 19, '2025-12-31', 1400000000.00, 0.0055, 0.0390, 0.1880, 0.1560, 1.2800, -0.1160, 0.0550, 1.0200),
-- P20 MS Long/Short
( 58, 20, '2024-12-31',  572000000.00, 0.0025, 0.0180, 0.0720, 0.0980, 0.8800, -0.0820, 0.0380, 0.5200),
( 59, 20, '2025-06-30',  586000000.00, 0.0012, 0.0085, 0.0420, 0.0950, 0.9100, -0.0620, 0.0340, 0.5300),
( 60, 20, '2025-12-31',  600000000.00, 0.0023, 0.0170, 0.0760, 0.0960, 0.9400, -0.0780, 0.0400, 0.5200),
-- P21 TRP Capital Appreciation
( 61, 21, '2024-12-31', 1040000000.00, 0.0058, 0.0410, 0.1650, 0.1680, 1.1500, -0.1180, 0.0480, 1.0800),
( 62, 21, '2025-06-30', 1069000000.00, 0.0027, 0.0200, 0.0960, 0.1650, 1.1800, -0.0880, 0.0440, 1.0900),
( 63, 21, '2025-12-31', 1100000000.00, 0.0052, 0.0370, 0.1740, 0.1700, 1.2100, -0.1120, 0.0510, 1.0800),
-- P22 TRP Equity Income
( 64, 22, '2024-12-31',  665000000.00, 0.0025, 0.0190, 0.0750, 0.1050, 0.8600, -0.0880, 0.0220, 0.8400),
( 65, 22, '2025-06-30',  681000000.00, 0.0012, 0.0090, 0.0440, 0.1020, 0.8900, -0.0660, 0.0200, 0.8500),
( 66, 22, '2025-12-31',  700000000.00, 0.0023, 0.0180, 0.0800, 0.1040, 0.9200, -0.0840, 0.0230, 0.8400),
-- P23 Wellington Quality Growth
( 67, 23, '2024-12-31', 1510000000.00, 0.0062, 0.0440, 0.1820, 0.1620, 1.2300, -0.1280, 0.0560, 1.0500),
( 68, 23, '2025-06-30', 1556000000.00, 0.0029, 0.0220, 0.1060, 0.1590, 1.2600, -0.0960, 0.0520, 1.0600),
( 69, 23, '2025-12-31', 1600000000.00, 0.0057, 0.0400, 0.1940, 0.1640, 1.3000, -0.1200, 0.0600, 1.0500),
-- P24 Wellington Strategic Value
( 70, 24, '2024-12-31',  855000000.00, 0.0022, 0.0165, 0.0680, 0.1080, 0.8300, -0.0920, 0.0180, 0.8600),
( 71, 24, '2025-06-30',  876000000.00, 0.0011, 0.0078, 0.0400, 0.1050, 0.8600, -0.0690, 0.0160, 0.8700),
( 72, 24, '2025-12-31',  900000000.00, 0.0021, 0.0155, 0.0720, 0.1060, 0.8900, -0.0870, 0.0190, 0.8600),
-- P25 Wellington Commodities
( 73, 25, '2024-12-31', 1140000000.00, 0.0028, 0.0220, 0.0880, 0.1520, 0.7200, -0.1380, 0.0220, 0.7500),
( 74, 25, '2025-06-30', 1170000000.00, 0.0013, 0.0100, 0.0520, 0.1490, 0.7500, -0.1050, 0.0200, 0.7600),
( 75, 25, '2025-12-31', 1200000000.00, 0.0026, 0.0200, 0.0940, 0.1500, 0.7800, -0.1300, 0.0240, 0.7500),
-- P26 Bridgewater All Weather
( 76, 26, '2024-12-31',14200000000.00, 0.0018, 0.0140, 0.0580, 0.0820, 0.8500, -0.0920, 0.0180, 0.5800),
( 77, 26, '2025-06-30',14600000000.00, 0.0009, 0.0070, 0.0340, 0.0800, 0.8800, -0.0700, 0.0160, 0.5900),
( 78, 26, '2025-12-31',15000000000.00, 0.0016, 0.0130, 0.0620, 0.0810, 0.9100, -0.0870, 0.0190, 0.5800),
-- P27 Bridgewater Pure Alpha
( 79, 27, '2024-12-31', 7700000000.00, 0.0035, 0.0280, 0.1150, 0.1250, 1.2800, -0.1050, 0.0820, 0.2200),
( 80, 27, '2025-06-30', 7850000000.00, 0.0016, 0.0130, 0.0680, 0.1220, 1.3100, -0.0800, 0.0780, 0.2300),
( 81, 27, '2025-12-31', 8000000000.00, 0.0032, 0.0260, 0.1220, 0.1240, 1.3500, -0.0990, 0.0850, 0.2200),
-- P28 Renaissance Institutional
( 82, 28, '2024-12-31', 4750000000.00, 0.0088, 0.0620, 0.2850, 0.1980, 1.6200, -0.1520, 0.1250, 0.8800),
( 83, 28, '2025-06-30', 4875000000.00, 0.0042, 0.0310, 0.1650, 0.1940, 1.6500, -0.1150, 0.1180, 0.8900),
( 84, 28, '2025-12-31', 5000000000.00, 0.0081, 0.0570, 0.3020, 0.2010, 1.6900, -0.1450, 0.1320, 0.8800),
-- P29 Renaissance Macro
( 85, 29, '2024-12-31', 2850000000.00, 0.0045, 0.0340, 0.1420, 0.1580, 1.1800, -0.1280, 0.0680, 0.6200),
( 86, 29, '2025-06-30', 2925000000.00, 0.0021, 0.0160, 0.0830, 0.1550, 1.2100, -0.0970, 0.0640, 0.6300),
( 87, 29, '2025-12-31', 3000000000.00, 0.0042, 0.0320, 0.1510, 0.1560, 1.2500, -0.1220, 0.0720, 0.6200),
-- P30 Citadel Global Equities
( 88, 30, '2024-12-31', 7680000000.00, 0.0052, 0.0380, 0.1650, 0.1420, 1.3500, -0.1350, 0.0820, 0.7200),
( 89, 30, '2025-06-30', 7840000000.00, 0.0025, 0.0190, 0.0960, 0.1390, 1.3800, -0.1030, 0.0780, 0.7300),
( 90, 30, '2025-12-31', 8000000000.00, 0.0048, 0.0350, 0.1750, 0.1400, 1.4200, -0.1290, 0.0860, 0.7200),
-- P31 Citadel Fixed Income
( 91, 31, '2024-12-31', 4760000000.00,-0.0008, 0.0055,-0.0150, 0.0620, 0.5200, -0.1020, 0.0150, 0.9100),
( 92, 31, '2025-06-30', 4880000000.00, 0.0005, 0.0030, 0.0120, 0.0600, 0.5500, -0.0790, 0.0160, 0.9200),
( 93, 31, '2025-12-31', 5000000000.00,-0.0005, 0.0060,-0.0080, 0.0610, 0.5300, -0.0970, 0.0155, 0.9100),
-- P32 Two Sigma Factor
( 94, 32, '2024-12-31', 3800000000.00, 0.0065, 0.0460, 0.1920, 0.1650, 1.3800, -0.1350, 0.0750, 0.9800),
( 95, 32, '2025-06-30', 3900000000.00, 0.0031, 0.0230, 0.1120, 0.1620, 1.4100, -0.1020, 0.0710, 0.9900),
( 96, 32, '2025-12-31', 4000000000.00, 0.0060, 0.0430, 0.2040, 0.1680, 1.4500, -0.1280, 0.0790, 0.9800),
-- P33 Two Sigma Event
( 97, 33, '2024-12-31', 1900000000.00, 0.0058, 0.0410, 0.1720, 0.1820, 1.1500, -0.1520, 0.0680, 0.8800),
( 98, 33, '2025-06-30', 1950000000.00, 0.0028, 0.0200, 0.1000, 0.1780, 1.1800, -0.1160, 0.0640, 0.8900),
( 99, 33, '2025-12-31', 2000000000.00, 0.0053, 0.0380, 0.1820, 0.1840, 1.2200, -0.1450, 0.0720, 0.8800),
-- P34 AQR Momentum
(100, 34, '2024-12-31', 5700000000.00, 0.0072, 0.0510, 0.2250, 0.1950, 1.4200, -0.1450, 0.0880, 1.0500),
(101, 34, '2025-06-30', 5850000000.00, 0.0034, 0.0255, 0.1310, 0.1920, 1.4500, -0.1100, 0.0840, 1.0600),
(102, 34, '2025-12-31', 6000000000.00, 0.0066, 0.0470, 0.2380, 0.1980, 1.4900, -0.1380, 0.0920, 1.0500),
-- P35 AQR Risk Parity
(103, 35, '2024-12-31', 3800000000.00, 0.0022, 0.0170, 0.0720, 0.0920, 1.0500, -0.0980, 0.0380, 0.4800),
(104, 35, '2025-06-30', 3900000000.00, 0.0011, 0.0085, 0.0420, 0.0900, 1.0800, -0.0750, 0.0350, 0.4900),
(105, 35, '2025-12-31', 4000000000.00, 0.0020, 0.0160, 0.0760, 0.0910, 1.1100, -0.0930, 0.0400, 0.4800),
-- P36 GPFG Global Equity
(106, 36, '2024-12-31',760000000000.00,0.0045, 0.0330, 0.1420, 0.1380, 1.0800, -0.1120, 0.0150, 0.9800),
(107, 36, '2025-06-30',780000000000.00,0.0021, 0.0160, 0.0830, 0.1350, 1.1100, -0.0850, 0.0130, 0.9900),
(108, 36, '2025-12-31',800000000000.00,0.0042, 0.0310, 0.1510, 0.1360, 1.1500, -0.1070, 0.0160, 0.9800),
-- P37 GPFG Fixed Income
(109, 37, '2024-12-31',257000000000.00,-0.0006,0.0050,-0.0100, 0.0620, 0.4800, -0.1050,-0.0020, 0.9400),
(110, 37, '2025-06-30',263000000000.00, 0.0004,0.0030, 0.0120, 0.0600, 0.5100, -0.0810,-0.0010, 0.9500),
(111, 37, '2025-12-31',270000000000.00,-0.0004,0.0055,-0.0060, 0.0610, 0.4900, -0.0990,-0.0015, 0.9400),
-- P38 GPFG Real Estate
(112, 38, '2024-12-31', 28500000000.00,0.0018, 0.0140, 0.0620, 0.1180, 0.7200, -0.1250, 0.0180, 0.8800),
(113, 38, '2025-06-30', 29250000000.00,0.0009, 0.0070, 0.0360, 0.1150, 0.7500, -0.0960, 0.0160, 0.8900),
(114, 38, '2025-12-31', 30000000000.00,0.0017, 0.0130, 0.0660, 0.1160, 0.7800, -0.1190, 0.0190, 0.8800),
-- P39 ADIA Global
(115, 39, '2024-12-31',332000000000.00,0.0032, 0.0240, 0.0980, 0.1120, 0.9200, -0.1020, 0.0120, 0.8800),
(116, 39, '2025-06-30',341000000000.00,0.0015, 0.0120, 0.0580, 0.1090, 0.9500, -0.0780, 0.0110, 0.8900),
(117, 39, '2025-12-31',350000000000.00,0.0030, 0.0225, 0.1040, 0.1100, 0.9800, -0.0970, 0.0130, 0.8800),
-- P40 ADIA EM
(118, 40, '2024-12-31',123000000000.00,0.0038, 0.0290, 0.1120, 0.1780, 0.7500, -0.1580, 0.0250, 0.9600),
(119, 40, '2025-06-30',126500000000.00,0.0018, 0.0140, 0.0660, 0.1750, 0.7800, -0.1210, 0.0220, 0.9700),
(120, 40, '2025-12-31',130000000000.00,0.0035, 0.0270, 0.1190, 0.1760, 0.8100, -0.1510, 0.0270, 0.9600),
-- P41 CalPERS Global Equity
(121, 41, '2024-12-31',265000000000.00,0.0040, 0.0295, 0.1230, 0.1350, 1.0200, -0.1120, 0.0130, 0.9700),
(122, 41, '2025-06-30',272000000000.00,0.0019, 0.0145, 0.0720, 0.1320, 1.0500, -0.0860, 0.0120, 0.9800),
(123, 41, '2025-12-31',280000000000.00,0.0037, 0.0275, 0.1300, 0.1330, 1.0800, -0.1070, 0.0140, 0.9700),
-- P42 CalPERS Growth
(124, 42, '2024-12-31', 47500000000.00,0.0068, 0.0480, 0.2050, 0.1880, 1.3200, -0.1380, 0.0620, 1.1500),
(125, 42, '2025-06-30', 48750000000.00,0.0032, 0.0240, 0.1190, 0.1850, 1.3500, -0.1050, 0.0580, 1.1600),
(126, 42, '2025-12-31', 50000000000.00,0.0062, 0.0450, 0.2180, 0.1900, 1.3900, -0.1310, 0.0660, 1.1500),
-- P43 CalPERS Fixed Income
(127, 43, '2024-12-31', 76000000000.00,-0.0007,0.0052,-0.0130, 0.0590, 0.4600, -0.1020,-0.0025, 0.9500),
(128, 43, '2025-06-30', 78000000000.00, 0.0005,0.0032, 0.0140, 0.0570, 0.4900, -0.0790,-0.0010, 0.9600),
(129, 43, '2025-12-31', 80000000000.00,-0.0005,0.0060,-0.0070, 0.0580, 0.4700, -0.0970,-0.0018, 0.9500),
-- P44 OTPP Public Equities
(130, 44, '2024-12-31', 76000000000.00,0.0042, 0.0310, 0.1280, 0.1380, 1.0500, -0.1150, 0.0180, 0.9900),
(131, 44, '2025-06-30', 78000000000.00,0.0020, 0.0155, 0.0750, 0.1350, 1.0800, -0.0880, 0.0160, 1.0000),
(132, 44, '2025-12-31', 80000000000.00,0.0039, 0.0295, 0.1360, 0.1360, 1.1100, -0.1100, 0.0190, 0.9900),
-- P45 OTPP Infrastructure
(133, 45, '2024-12-31', 38000000000.00,0.0015, 0.0115, 0.0480, 0.0820, 0.7800, -0.0920, 0.0180, 0.6500),
(134, 45, '2025-06-30', 39000000000.00,0.0008, 0.0058, 0.0280, 0.0800, 0.8100, -0.0710, 0.0160, 0.6600),
(135, 45, '2025-12-31', 40000000000.00,0.0014, 0.0108, 0.0510, 0.0810, 0.8400, -0.0880, 0.0190, 0.6500),
-- P46 OTPP Fixed Income
(136, 46, '2024-12-31', 57000000000.00,-0.0005,0.0048,-0.0090, 0.0600, 0.5200, -0.0980,-0.0015, 0.9400),
(137, 46, '2025-06-30', 58500000000.00, 0.0004,0.0028, 0.0110, 0.0580, 0.5500, -0.0760,-0.0008, 0.9500),
(138, 46, '2025-12-31', 60000000000.00,-0.0003,0.0055,-0.0050, 0.0590, 0.5300, -0.0930,-0.0012, 0.9400),
-- P47 Rockefeller ESG
(139, 47, '2024-12-31', 2840000000.00, 0.0062, 0.0440, 0.1850, 0.1650, 1.2500, -0.1280, 0.0580, 1.0400),
(140, 47, '2025-06-30', 2920000000.00, 0.0029, 0.0220, 0.1080, 0.1620, 1.2800, -0.0970, 0.0540, 1.0500),
(141, 47, '2025-12-31', 3000000000.00, 0.0057, 0.0405, 0.1960, 0.1660, 1.3200, -0.1220, 0.0620, 1.0400),
-- P48 Rockefeller Dividend
(142, 48, '2024-12-31', 1900000000.00, 0.0024, 0.0182, 0.0760, 0.1020, 0.9100, -0.0880, 0.0220, 0.8300),
(143, 48, '2025-06-30', 1950000000.00, 0.0012, 0.0088, 0.0450, 0.1000, 0.9400, -0.0670, 0.0200, 0.8400),
(144, 48, '2025-12-31', 2000000000.00, 0.0022, 0.0170, 0.0810, 0.1010, 0.9700, -0.0840, 0.0230, 0.8300),
-- P49 Rockefeller Market Neutral
(145, 49, '2024-12-31',  478000000.00, 0.0018, 0.0135, 0.0580, 0.0680, 1.1500, -0.0620, 0.0420, 0.1800),
(146, 49, '2025-06-30',  489000000.00, 0.0009, 0.0065, 0.0340, 0.0660, 1.1800, -0.0480, 0.0390, 0.1900),
(147, 49, '2025-12-31',  500000000.00, 0.0017, 0.0125, 0.0620, 0.0670, 1.2100, -0.0590, 0.0450, 0.1800),
-- P50 Rockefeller Commodities
(148, 50, '2024-12-31',  285000000.00, 0.0032, 0.0255, 0.1080, 0.1920, 0.6800, -0.1550, 0.0280, 0.5500),
(149, 50, '2025-06-30',  292000000.00, 0.0015, 0.0122, 0.0640, 0.1890, 0.7100, -0.1190, 0.0250, 0.5600),
(150, 50, '2025-12-31',  300000000.00, 0.0030, 0.0240, 0.1150, 0.1900, 0.7400, -0.1480, 0.0300, 0.5500);
SET IDENTITY_INSERT Portfolio_Performance OFF;

-- â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
-- STEP 7: 15 Market Events
-- event_type:  natural_disaster | earnings | regulatory | economic | sectoral | geopolitical | policy
-- impact_level: low | medium | high
-- sentiment:   positive | negative | neutral
-- â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
SET IDENTITY_INSERT Market_Events ON;
INSERT INTO Market_Events (event_id, event_date, event_type, event_title, event_description, affected_sectors, affected_regions, impact_level, sentiment) VALUES
( 1, '2025-01-29 14:00:00', 'policy',      'Federal Reserve Holds Rates at 4.25-4.50%',
   'FOMC decision to hold rates steady amid mixed inflation signals. Chair Powell signaled caution on future cuts.',
   'Financials,Real Estate,Utilities', 'United States', 'high', 'neutral'),
( 2, '2025-02-26 16:30:00', 'earnings',    'NVIDIA Q4 2024 Earnings Beat â€” AI Revenue Surges',
   'NVIDIA reported $39.3B revenue (+78% YoY), driven by data center AI chip demand. H100/H200 backlog remains elevated.',
   'Technology,Semiconductors', 'Global', 'high', 'positive'),
( 3, '2025-03-04 09:00:00', 'geopolitical','U.S. Announces Sweeping 25% Tariffs on China Imports',
   'White House issued executive order imposing broad tariffs on Chinese goods, escalating trade tensions and supply chain concerns.',
   'Technology,Consumer Discretionary,Industrials', 'United States,China,Asia', 'high', 'negative'),
( 4, '2025-04-02 16:30:00', 'geopolitical','Liberation Day â€” Global Reciprocal Tariff Announcement',
   'President Trump announced reciprocal tariffs on 60+ countries. Markets sold off sharply with S&P 500 falling 4.8% on the day.',
   'All Sectors', 'Global', 'high', 'negative'),
( 5, '2025-05-01 16:30:00', 'earnings',    'Apple Q2 2025 Earnings In-Line; Services Revenue Record',
   'Apple reported $95.4B revenue (+5% YoY). Services segment hit all-time high of $26.6B. AI features drove iPhone upgrade cycle.',
   'Technology,Consumer Discretionary', 'Global', 'medium', 'positive'),
( 6, '2025-05-12 00:00:00', 'policy',      'U.S.-China 90-Day Trade Truce Announced',
   'Treasury Secretary Bessent and Chinese Vice Premier He Lifeng agreed to a temporary reduction of tariffs, pausing escalation.',
   'Technology,Consumer Discretionary,Industrials', 'United States,China', 'high', 'positive'),
( 7, '2025-05-13 10:00:00', 'regulatory',  'EU AI Act Enforcement Phase Begins',
   'European Union began enforcement of the AI Act, requiring model providers to register high-risk AI systems. Compliance costs rise.',
   'Technology', 'European Union', 'medium', 'negative'),
( 8, '2025-06-10 00:00:00', 'sectoral',    'Energy Sector Rally on OPEC+ Production Cut Extension',
   'OPEC+ unanimously extended 3.66 mbpd production cuts through end of 2025, pushing Brent crude above $82/barrel.',
   'Energy', 'Global', 'medium', 'positive'),
( 9, '2025-06-18 14:00:00', 'policy',      'Federal Reserve June Rate Hold â€” Dot Plot Revised Down',
   'FOMC held at 4.25-4.50%. Revised dot plot now projects two 25bp cuts in H2 2025, less than prior three-cut forecast.',
   'Financials,Real Estate,Utilities', 'United States', 'medium', 'neutral'),
(10, '2025-07-30 16:30:00', 'earnings',    'Microsoft Q4 FY2025 Earnings Beat on Azure AI Growth',
   'Microsoft reported $73.7B revenue (+15% YoY). Azure grew 35% driven by AI workloads. Copilot seats crossed 400M.',
   'Technology,Cloud', 'Global', 'high', 'positive'),
(11, '2025-07-31 08:30:00', 'economic',    'U.S. GDP Q2 2025 Advance Estimate: +2.8% Annualized',
   'BEA advance estimate showed economy growing 2.8% in Q2, above the 2.3% consensus. Consumer spending remained resilient.',
   'All Sectors', 'United States', 'high', 'positive'),
(12, '2025-09-12 00:00:00', 'sectoral',    'Healthcare Sector Selloff â€” PBM Reform Bill Advances',
   'Senate advanced pharmacy benefit manager reform legislation, threatening drug pricing power. Healthcare ETF (XLV) fell 3.2%.',
   'Healthcare,Pharmaceuticals', 'United States', 'medium', 'negative'),
(13, '2025-09-17 14:00:00', 'policy',      'Federal Reserve Cuts Rates 25bp to 4.00-4.25%',
   'First cut since 2024 as inflation moved toward 2% target. Soft landing narrative solidified. Markets rallied on the decision.',
   'Financials,Real Estate,Utilities,Consumer Discretionary', 'United States', 'high', 'positive'),
(14, '2025-11-13 08:30:00', 'economic',    'October CPI Rises 0.4% â€” Core Inflation Stays Sticky',
   'CPI came in hotter than expected at +3.2% YoY. Core services ex-shelter remained elevated, complicating Fed cut expectations.',
   'All Sectors', 'United States', 'high', 'negative'),
(15, '2025-12-15 00:00:00', 'earnings',    'Q4 2025 Mega-Cap Tech Earnings Season Begins',
   'Opening of Q4 earnings season with AAPL, MSFT, GOOGL, META all beating estimates. AI monetization evident across all platforms.',
   'Technology,Communication Services', 'Global', 'high', 'positive');
SET IDENTITY_INSERT Market_Events OFF;

PRINT 'Transactions, Portfolio_Performance, and Market_Events inserted successfully.';

-- ─────────────────────────────────────────────────────────────────────────────
-- STEP 8: Users (fund managers) + Portfolios.manager_id (multi-tenant access)
-- On a fresh install this table/column won't exist yet, so no IF NOT EXISTS
-- guards are needed here (unlike db_migration_auth.sql, which is the script
-- actually run against an already-populated production DB — see that file's
-- header for why the two are kept separate).
-- role: fund_manager | admin. Shared demo password 'FinSight2026!' — see AUTH.md.
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE Users (
    user_id         INT IDENTITY(1,1) PRIMARY KEY,
    email           VARCHAR(255) NOT NULL UNIQUE,
    hashed_password VARCHAR(255) NOT NULL,
    full_name       VARCHAR(255) NOT NULL,
    role            VARCHAR(20)  NOT NULL CHECK (role IN ('fund_manager', 'admin')),
    created_at      DATETIME NOT NULL DEFAULT GETUTCDATE()
);
GO

INSERT INTO Users (email, hashed_password, full_name, role) VALUES
('sarah.chen@finsight.demo',     '$2b$12$d94X9qQeMw2TxMm8z32Hp.IhbfbXO9MCOgUAJOOjhqW8FrIgFyEii', 'Sarah Chen',     'fund_manager'),
('james.okafor@finsight.demo',   '$2b$12$d94X9qQeMw2TxMm8z32Hp.IhbfbXO9MCOgUAJOOjhqW8FrIgFyEii', 'James Okafor',   'fund_manager'),
('priya.patel@finsight.demo',    '$2b$12$d94X9qQeMw2TxMm8z32Hp.IhbfbXO9MCOgUAJOOjhqW8FrIgFyEii', 'Priya Patel',    'fund_manager'),
('david.kim@finsight.demo',      '$2b$12$d94X9qQeMw2TxMm8z32Hp.IhbfbXO9MCOgUAJOOjhqW8FrIgFyEii', 'David Kim',      'fund_manager'),
('elena.rodriguez@finsight.demo','$2b$12$d94X9qQeMw2TxMm8z32Hp.IhbfbXO9MCOgUAJOOjhqW8FrIgFyEii', 'Elena Rodriguez','fund_manager'),
('admin@finsight.demo',          '$2b$12$d94X9qQeMw2TxMm8z32Hp.IhbfbXO9MCOgUAJOOjhqW8FrIgFyEii', 'Marcus Webb',    'admin');
GO

ALTER TABLE Portfolios ADD manager_id INT NULL;
GO
ALTER TABLE Portfolios ADD CONSTRAINT FK_Portfolios_Manager
    FOREIGN KEY (manager_id) REFERENCES Users(user_id);
GO

DECLARE @sarah INT = (SELECT user_id FROM Users WHERE email = 'sarah.chen@finsight.demo');
DECLARE @james INT = (SELECT user_id FROM Users WHERE email = 'james.okafor@finsight.demo');
DECLARE @priya INT = (SELECT user_id FROM Users WHERE email = 'priya.patel@finsight.demo');
DECLARE @david INT = (SELECT user_id FROM Users WHERE email = 'david.kim@finsight.demo');
DECLARE @elena INT = (SELECT user_id FROM Users WHERE email = 'elena.rodriguez@finsight.demo');

UPDATE Portfolios SET manager_id = @sarah WHERE portfolio_id BETWEEN 1  AND 10;
UPDATE Portfolios SET manager_id = @james WHERE portfolio_id BETWEEN 11 AND 20;
UPDATE Portfolios SET manager_id = @priya WHERE portfolio_id BETWEEN 21 AND 30;
UPDATE Portfolios SET manager_id = @david WHERE portfolio_id BETWEEN 31 AND 40;
UPDATE Portfolios SET manager_id = @elena WHERE portfolio_id BETWEEN 41 AND 50;

PRINT 'Users seeded and Portfolios.manager_id backfilled.';
PRINT '';
PRINT 'Row counts:';
SELECT 'Customers'           AS [Table], COUNT(*) AS [Rows] FROM Customers
UNION ALL SELECT 'Portfolios',         COUNT(*) FROM Portfolios
UNION ALL SELECT 'Securities',         COUNT(*) FROM Securities
UNION ALL SELECT 'Positions',          COUNT(*) FROM Positions
UNION ALL SELECT 'Transactions',       COUNT(*) FROM Transactions
UNION ALL SELECT 'Portfolio_Performance', COUNT(*) FROM Portfolio_Performance
UNION ALL SELECT 'Market_Events',      COUNT(*) FROM Market_Events
UNION ALL SELECT 'Users',              COUNT(*) FROM Users;

