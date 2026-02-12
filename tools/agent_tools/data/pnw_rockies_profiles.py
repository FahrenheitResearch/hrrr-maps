"""PNW & Northern Rockies Fire-Vulnerable City Profiles
=======================================================

Comprehensive terrain, evacuation, fire behavior, infrastructure, and demographic
data for 76 fire-vulnerable cities across Oregon, Washington, Idaho, and Montana.
Profiles derived from CWPP documents, InciWeb records, NWCG incident reports,
state forestry data, and post-fire assessments.

Usage:
    from tools.agent_tools.data.pnw_rockies_profiles import (
        PNW_TERRAIN_PROFILES,
        PNW_IGNITION_SOURCES,
        PNW_CLIMATOLOGY,
    )

Cities covered (76 entries across 4 states):
    OREGON (43 cities):
        Baker City
        Bend
        Blue River
        Bly
        Bonanza
        Camp Sherman
        Canyon City
        Chiloquin
        Cottage Grove
        Detroit
        Drain
        Dufur
        Enterprise
        Florence
        Gates
        Grants Pass
        Grass Valley
        Hood River
        Jacksonville
        John Day
        Joseph
        Klamath Falls
        La Grande
        La Pine
        Lakeview
        Maupin
        McKenzie Bridge
        Medford Ashland
        Mosier
        Myrtle Creek
        Oakridge
        Paisley
        Pendleton
        Phoenix
        Prairie City
        Redmond
        Roseburg
        Sisters
        Sunriver
        Sweet Home
        Talent
        The Dalles
        Vida
    WASHINGTON (12 cities):
        Chelan
        Cle Elum
        Ellensburg
        Entiat
        Leavenworth
        Manson
        Omak Okanogan
        Pateros
        Roslyn
        Twisp
        Wenatchee
        Winthrop
    IDAHO (10 cities):
        Boise
        Cascade
        Featherville Pine
        Garden Valley
        Hailey
        Ketchum Sun Valley
        Lowman
        Mccall
        Salmon
        Stanley
    MONTANA (11 cities):
        Hamilton
        Helena
        Kalispell Whitefish
        Lincoln
        Lolo
        Missoula
        Red Lodge
        Seeley Lake
        Stevensville
        Superior
        West Yellowstone

Sources:
    - Oregon CWPP documents, ODF incident reports
    - Washington DNR fire records, WADNR CWPP data
    - Idaho Dept of Lands fire history, USFS incident reports
    - Montana DNRC fire records, Flathead/Missoula County CWPPs
    - InciWeb, NIFC, NWCG incident data
    - WRCC / IEM / ASOS climatology archives
    - Wikipedia fire articles with citations
"""

# =============================================================================
# TERRAIN PROFILES -- 47 entries organized by state
# =============================================================================

PNW_TERRAIN_PROFILES = {

    # =========================================================================
    # OREGON (14 cities)
    # =========================================================================

    # =========================================================================
    # 1. BEND, OR — Cascade Edge WUI, Central Oregon's Largest City
    # =========================================================================
    "bend_or": {
        "center": [44.0582, -121.3153],
        "terrain_notes": (
            "Bend sits at 3,623 ft on the eastern flank of the Cascade Range, straddling "
            "the Deschutes River where high-desert juniper/sagebrush transitions to ponderosa "
            "pine and mixed conifer. The western city boundary directly abuts Deschutes National "
            "Forest, creating one of Oregon's most extensive wildland-urban interface zones. "
            "Skyline Forest (3,700 acres of ponderosa pine) borders the northwest city limits "
            "and burned in the 2014 Two Bulls Fire. Tumalo Creek and the Deschutes River "
            "corridors funnel winds from the Cascades into residential areas. The west side "
            "neighborhoods (Century West, Summit West, Shevlin) are built into continuous "
            "forest with heavy fuel loading. Lava rock terrain and volcanic soils create "
            "irregular topography with pockets of dense fuel that complicate fire suppression. "
            "The city has grown rapidly from ~20K (1990) to ~107K (2024), with much of the "
            "growth pushing into forested WUI zones on the west and south sides."
        ),
        "key_features": [
            {"name": "Deschutes River Canyon", "bearing": "N-S through city", "type": "river_corridor",
             "notes": "Major fuel corridor bisecting city; riparian vegetation creates continuous fuel"},
            {"name": "Skyline Forest / Shevlin Park", "bearing": "NW", "type": "forest_interface",
             "notes": "3,700-acre ponderosa forest directly adjoining city; Two Bulls Fire 2014 burned through this area"},
            {"name": "Tumalo Creek Corridor", "bearing": "W", "type": "drainage_corridor",
             "notes": "Funnels downslope winds from Cascades into residential areas; dense riparian fuels"},
            {"name": "Phil's Trailhead / West Bend WUI", "bearing": "W-SW", "type": "recreation_wui",
             "notes": "Heavy recreation use area where forest meets dense housing developments"},
            {"name": "Century Drive / Mt. Bachelor Corridor", "bearing": "SW", "type": "evacuation_corridor",
             "notes": "Single road to Mt. Bachelor resort; corridor through continuous national forest"},
            {"name": "Pilot Butte", "bearing": "E", "type": "landmark",
             "notes": "Cinder cone (4,138 ft) providing panoramic fire-spotting vantage; eastern city boundary"},
        ],
        "elevation_range_ft": [3400, 4200],
        "wui_exposure": "extreme",
        "historical_fires": [
            {"name": "Awbrey Hall Fire", "year": 1990, "acres": 3349,
             "details": "Arson-caused fire on August 4; destroyed 22 homes, evacuated 2,800 residents in 12 hours. "
                        "Led directly to Oregon SB 360 (1997) Forestland-Urban Interface Fire Protection Act. "
                        "Burned through ponderosa pine on west side of Bend."},
            {"name": "Two Bulls Fire", "year": 2014, "acres": 6900,
             "details": "Burned through Skyline Forest NW of city; human-caused. No structures lost but forced "
                        "hundreds of evacuations, threatened water supply from Tumalo Creek, degraded air quality. "
                        "Demonstrated vulnerability of west-side WUI."},
            {"name": "Darlene 3 Fire", "year": 2024, "acres": 3900,
             "details": "Burned in Deschutes NF ~30 miles south near La Pine; over 1,000 homes on evacuation "
                        "alert. Demonstrated ongoing regional fire risk."},
            {"name": "Bachelor Complex (Little Lava Fire)", "year": 2024, "acres": 2500,
             "details": "Threatened Sunriver and SW Bend; Level 2 evacuations for Deschutes River communities "
                        "along South Century Drive."},
        ],
        "evacuation_routes": [
            {"route": "US-97 (Bend Parkway)", "direction": "N-S", "lanes": 4,
             "bottleneck": "Interchanges at Revere Ave, Colorado Ave become gridlocked in peak traffic",
             "risk": "Primary N-S corridor; if fire approaches from west, eastward evacuation funnels all traffic to US-97"},
            {"route": "US-20 (Greenwood Ave)", "direction": "E-W", "lanes": 2,
             "bottleneck": "Two-lane highway east of Bend; limited capacity for mass evacuation",
             "risk": "Only east-west route north of city; passes through high-fire-risk juniper terrain"},
            {"route": "Century Drive (OR-372)", "direction": "SW", "lanes": 2,
             "bottleneck": "Single two-lane road through continuous national forest to Mt. Bachelor",
             "risk": "Dead-end corridor; 15,000+ recreation visitors on peak days with no alternative egress"},
            {"route": "OR-97 South (toward La Pine)", "direction": "S", "lanes": 2,
             "bottleneck": "Two-lane highway through ponderosa pine forest; Sunriver and La Pine also evacuating",
             "risk": "Shared corridor with 25,000+ residents and visitors to the south; cascading evacuation failure risk"},
        ],
        "fire_spread_characteristics": {
            "primary_wind_regime": (
                "East/northeast winds during offshore (east wind) events drive fires from Cascades into city. "
                "Afternoon SW thermal winds in summer push fires upslope toward west-side neighborhoods. "
                "Diurnal wind shift creates complex fire behavior at WUI boundary."
            ),
            "critical_corridors": [
                "Tumalo Creek drainage — funnels wind and fire from Cascades directly into west Bend",
                "Deschutes River canyon — N-S fire spread corridor through heart of city",
                "Skyline Forest / Shevlin Park — continuous canopy connecting national forest to city",
                "Century Drive corridor — fire can race along highway corridor from Mt. Bachelor area",
            ],
            "rate_of_spread_potential": (
                "High in ponderosa pine / juniper: 50-150 chains/hr under wind-driven conditions. "
                "2014 Two Bulls Fire grew from ignition to 6,000+ acres in 48 hours. "
                "Awbrey Hall Fire burned 3,350 acres in 12 hours with residential involvement."
            ),
            "spotting_distance": (
                "0.5-1.5 miles in ponderosa pine; bark and ember transport from canopy fires "
                "readily ignites shake/wood roofs in older west-side neighborhoods. "
                "Volcanic terrain creates updrafts enhancing spotting distance."
            ),
        },
        "infrastructure_vulnerabilities": {
            "water_system": (
                "City water sourced from Bridge Creek and Tumalo Creek; both intakes in forested "
                "watersheds vulnerable to fire contamination. Two Bulls Fire (2014) directly "
                "threatened Tumalo Creek water supply. Post-fire debris flows can compromise "
                "water quality for months."
            ),
            "power": (
                "Pacific Power distribution; overhead lines through forested corridors on west side. "
                "Central Electric Cooperative serves rural areas. Fire-related outages common; "
                "2020 east wind event caused cascading power failures across Central Oregon."
            ),
            "communications": (
                "Cell towers on Awbrey Butte and Pilot Butte; west-side towers in fire-prone "
                "forest. Deschutes 911 center serves entire county. Emergency alert system "
                "tested regularly but coverage gaps exist in canyon areas."
            ),
            "medical": (
                "St. Charles Bend Medical Center — 261 beds, Level II Trauma Center, largest "
                "hospital between Salem and Boise. Only regional hospital for 100+ mile radius; "
                "surge capacity limited during mass-casualty wildfire events."
            ),
        },
        "demographics_risk_factors": {
            "population": 106926,
            "seasonal_variation": (
                "Tourism doubles effective population in summer; 3+ million annual visitors to "
                "Mt. Bachelor, Deschutes River, and Cascade Lakes. Peak fire season coincides "
                "with peak tourism season (July-September)."
            ),
            "elderly_percentage": "~16% over 65",
            "mobile_homes": (
                "Several mobile home parks along US-97 corridor and in south Bend; "
                "approximately 5-7% of housing stock is manufactured homes."
            ),
            "special_needs_facilities": (
                "Multiple assisted living facilities on west side near WUI; Bend Senior Center; "
                "several group care homes in forested neighborhoods requiring evacuation assistance."
            ),
        },
    },

    # =========================================================================
    # 9. BLUE RIVER, OR — Holiday Farm Fire, Destroyed 2020
    # =========================================================================
    "blue_river_or": {
        "center": [44.1626, -122.3339],
        "terrain_notes": (
            "Blue River (~1,000 ft) is a small unincorporated community in the McKenzie River "
            "valley of Lane County, approximately 57 miles east of Eugene along Oregon Route 126. "
            "The community sits at the confluence of Blue River and the McKenzie River, in a "
            "narrow valley bounded by steep, heavily forested slopes of the Willamette National "
            "Forest. The terrain is dominated by dense Douglas-fir and western hemlock forest "
            "with heavy understory fuel loads. On September 7-8, 2020, the Holiday Farm Fire "
            "— ignited when power lines fell in extreme east winds — raced 27 miles down the "
            "McKenzie River corridor from near McKenzie Bridge through Blue River, Vida, Nimrod, "
            "and Leaburg. The fire destroyed over 500 homes and 768 total structures, including "
            "most of the structures in Blue River. The community has been slowly rebuilding, "
            "with new housing projects opening in 2025, five years after the fire."
        ),
        "key_features": [
            {"name": "McKenzie River", "bearing": "E-W through community", "type": "river_corridor",
             "notes": "Wild and Scenic River corridor; fire raced 27 miles down this valley in 2020"},
            {"name": "Blue River Reservoir", "bearing": "NE", "type": "reservoir",
             "notes": "Flood control reservoir; forested watershed above. Dam creates narrow canyon below."},
            {"name": "OR-126 (McKenzie Highway)", "bearing": "E-W", "type": "highway",
             "notes": "Only road through valley; Holiday Farm Fire paralleled and crossed highway repeatedly"},
            {"name": "Willamette National Forest", "bearing": "All directions", "type": "national_forest",
             "notes": "1.68 million acres of dense forest surrounds community; continuous canopy fuel from Cascades to valley floor"},
            {"name": "Vida / Nimrod / Leaburg", "bearing": "W (downstream)", "type": "communities",
             "notes": "Small communities downstream along McKenzie River also destroyed or damaged by Holiday Farm Fire"},
            {"name": "McKenzie Bridge", "bearing": "E (10 miles)", "type": "community",
             "notes": "Small community upstream; near fire's origin point. Remote with very limited evacuation options."},
        ],
        "elevation_range_ft": [900, 1200],
        "wui_exposure": "extreme",
        "historical_fires": [
            {"name": "Holiday Farm Fire", "year": 2020, "acres": 173393,
             "details": "Started Sept 7, 2020 around 7:45 PM near Holiday Farm RV Resort when power lines "
                        "fell in extreme east winds. Spread 27 miles down McKenzie River valley in ~12 hours. "
                        "Destroyed 768 structures including 517 homes. Killed 1 person (David Scott Perry, "
                        "59, in Vida). Burned 173,393 acres of Lane County forest and communities. "
                        "Federal lawsuit filed against Pacific Power/PacifiCorp for infrastructure failure. "
                        "Most structures in Blue River were destroyed."},
        ],
        "evacuation_routes": [
            {"route": "OR-126 West (toward Springfield/Eugene)", "direction": "W", "lanes": 2,
             "bottleneck": "Two-lane road through narrow river canyon for 50+ miles; passes through Vida, "
                          "Nimrod, Leaburg — all also on fire in 2020",
             "risk": "Only evacuation route for Blue River. During 2020 fire, residents had to drive through "
                     "fire zones. Road was impassable in some sections. ~57 miles to Eugene on winding canyon road."},
            {"route": "OR-126 East (toward McKenzie Bridge/Sisters)", "direction": "E", "lanes": 2,
             "bottleneck": "Climbs into mountains; very remote, no services. McKenzie Pass closed Oct-Jun.",
             "risk": "Leads deeper into forest and mountains. During 2020 fire, this direction led toward "
                     "the fire's origin. Not a viable evacuation route during east wind fire events."},
        ],
        "fire_spread_characteristics": {
            "primary_wind_regime": (
                "McKenzie River valley creates a natural wind funnel during east wind events. "
                "September 2020 demonstrated: east winds of 40-60 mph channeled down the valley, "
                "driving the fire 27 miles westward in approximately 12 hours. Normal summer "
                "pattern is gentle upvalley afternoon winds. The east wind events are episodic "
                "but catastrophic — capable of transforming a remote forest fire into a valley-wide "
                "conflagration in hours."
            ),
            "critical_corridors": [
                "McKenzie River valley — primary fire corridor; wind funnel during east wind events",
                "Blue River tributary drainage — fire pathway from surrounding forest into community",
                "OR-126 highway corridor — fire paralleled road through continuous forest",
                "Power line corridor — infrastructure failure created ignition ahead of fire front",
            ],
            "rate_of_spread_potential": (
                "Holiday Farm Fire demonstrated valley-corridor spread of 27 miles in ~12 hours, "
                "averaging over 2 miles per hour sustained. In the steep, forested terrain of "
                "the McKenzie corridor, crown fire runs exceeding 200 chains/hr. Upslope runs "
                "on valley walls can exceed 300 chains/hr. Continuous dense fuel load with no "
                "natural firebreaks in the valley."
            ),
            "spotting_distance": (
                "2-5 miles during extreme east wind events; massive ember production from "
                "old-growth and second-growth Douglas-fir crown fire. Power line failures "
                "created ignition 10+ miles ahead of fire front. Valley geometry concentrates "
                "embers in the narrow corridor."
            ),
        },
        "infrastructure_vulnerabilities": {
            "water_system": (
                "Small community water system destroyed in 2020 fire; rebuilt. Blue River "
                "water dependent on local wells and surface intake from Blue River. "
                "Post-fire sediment and debris contaminate watershed for years."
            ),
            "power": (
                "EWEB (Eugene Water & Electric Board) and Pacific Power serve area. "
                "Overhead lines through forested canyon; power line failure started the Holiday Farm Fire. "
                "Federal lawsuit against PacifiCorp for infrastructure failure. Single-corridor "
                "power supply with complete vulnerability to canyon fires."
            ),
            "communications": (
                "Extremely limited cell coverage in McKenzie valley. Canyon terrain blocks signals. "
                "During 2020 fire, power failure eliminated communications before many residents "
                "could be warned. Lane County emergency alerts reached some residents but many missed."
            ),
            "medical": (
                "No medical facilities. Nearest hospital: PeaceHealth Sacred Heart at RiverBend "
                "in Springfield (~55 miles west). During fire with road closures, completely "
                "isolated from medical care."
            ),
        },
        "demographics_risk_factors": {
            "population": 800,
            "seasonal_variation": (
                "McKenzie River recreation (fishing, rafting, hot springs) brings significant "
                "summer visitors. Cougar Reservoir and Blue River Reservoir attract campers. "
                "Population reduced post-fire; rebuilding ongoing as of 2025."
            ),
            "elderly_percentage": "~25% over 65 (rural retirement community character)",
            "mobile_homes": (
                "Pre-fire: significant manufactured homes and RV parks along Hwy 126 and river. "
                "Holiday Farm RV Resort (near fire's origin) destroyed. Rebuilt housing mostly "
                "permanent construction with improved fire resistance."
            ),
            "special_needs_facilities": (
                "None. No pharmacy, clinic, or senior services. Community entirely dependent on "
                "Springfield/Eugene for medical and social services — 55 miles away."
            ),
        },
    },

    # =========================================================================
    # 14. CAMP SHERMAN, OR — Metolius River, Surrounded by Forest
    # =========================================================================
    "camp_sherman_or": {
        "center": [44.4641, -121.6383],
        "terrain_notes": (
            "Camp Sherman (~2,963 ft) is a tiny unincorporated community in Jefferson County, "
            "nestled along the headwaters of the Metolius River approximately 15 miles northwest "
            "of Sisters. The community of ~250 year-round residents occupies 3.15 square miles "
            "of ponderosa pine forest within the Deschutes National Forest. Access is via Forest "
            "Road 14 off Highway 20, then Forest Road 1419 — approximately 12 miles from the "
            "nearest highway. The community is classified as 'extreme' fire risk in the Sisters "
            "Wildfire Protection Plan, with heavy fuel pockets to the west and north capable of "
            "promoting extreme fire behavior. The Metolius River, one of Oregon's most celebrated "
            "spring-fed streams, emerges from the base of Black Butte nearby. The surrounding "
            "forest has a history of fire suppression leading to dense understory accumulation. "
            "Nearly 20 large fires have threatened the greater Sisters/Camp Sherman area since "
            "1994, and the community was evacuated during the 2003 B&B Complex Fire."
        ),
        "key_features": [
            {"name": "Metolius River", "bearing": "Through community", "type": "spring_fed_river",
             "notes": "Iconic spring-fed river emerging from base of Black Butte; riparian corridor provides some fuel break"},
            {"name": "Black Butte", "bearing": "SE", "type": "volcanic_peak",
             "notes": "6,436 ft cinder cone; fire lookout tower. Dense forest on slopes connects to community."},
            {"name": "Green Ridge", "bearing": "E", "type": "ridgeline",
             "notes": "Prominent forested ridge; Green Ridge Fire (2020) threatened Camp Sherman from this direction"},
            {"name": "Mt. Jefferson Wilderness", "bearing": "NW", "type": "wilderness",
             "notes": "111,177 acres; B&B Complex Fire originated in this wilderness. No suppression until boundary."},
            {"name": "Deschutes National Forest", "bearing": "All directions", "type": "national_forest",
             "notes": "Community completely surrounded by national forest; no defensible perimeter"},
            {"name": "Forest Road 14 / 1419", "bearing": "SE to Hwy 20", "type": "access_road",
             "notes": "Only access road; ~12 miles of forest road to Highway 20. Single-point failure for evacuation."},
        ],
        "elevation_range_ft": [2900, 3100],
        "wui_exposure": "extreme",
        "historical_fires": [
            {"name": "B&B Complex Fire", "year": 2003, "acres": 90769,
             "details": "Two lightning-caused fires that burned 90,769 acres in central Cascades. "
                        "Camp Sherman was evacuated (~300 people). Fire burned ponderosa, lodgepole, "
                        "and Douglas-fir on both sides of Cascades. Cost $38.7M to suppress. "
                        "13 structures destroyed region-wide. Changed fire management philosophy."},
            {"name": "Green Ridge Fire", "year": 2020, "acres": 1000,
             "details": "During Labor Day east wind event. Fire on Green Ridge east of Camp Sherman "
                        "forced evacuation notices. Demonstrated ongoing vulnerability."},
            {"name": "Black Crater Fire", "year": 2006, "acres": 9300,
             "details": "Burned west of Sisters near Black Crater. Threatened broader Sisters/Camp Sherman area."},
        ],
        "evacuation_routes": [
            {"route": "Forest Road 14 South to Hwy 20", "direction": "SE", "lanes": 2,
             "bottleneck": "12 miles of paved forest road through continuous pine forest; ONLY road out. "
                          "Single-lane in sections. No alternative routes.",
             "risk": "CRITICAL: Single point of failure. If fire cuts FR 14, community is completely trapped. "
                     "Road passes through dense forest the entire distance. During B&B Complex evacuation, "
                     "residents drove through smoke on this road."},
            {"route": "Forest Roads North/West", "direction": "N/W", "lanes": 1,
             "bottleneck": "Unpaved forest roads; many are dead ends or lead to wilderness trailheads",
             "risk": "Not viable evacuation routes; lead deeper into forest and wilderness. "
                     "Could become fire traps. Some seasonal closures."},
        ],
        "fire_spread_characteristics": {
            "primary_wind_regime": (
                "Eastern Cascade foothills experience afternoon SW thermal winds in summer and "
                "periodic strong east wind events. The Metolius Basin creates local wind effects "
                "— cold air from the spring-fed river creates inversions that can trap smoke. "
                "During east wind events, fire approaches rapidly from the west (Cascades). "
                "Sisters CWPP rated Camp Sherman 'extreme risk' for fire behavior potential."
            ),
            "critical_corridors": [
                "Forest Road 14 corridor — sole access road through continuous ponderosa forest",
                "Green Ridge — elevated terrain to east; fire can descend toward community",
                "Metolius River drainage — northward fire corridor from Black Butte area",
                "Mt. Jefferson Wilderness approach — B&B Complex fire demonstrated this corridor",
            ],
            "rate_of_spread_potential": (
                "In ponderosa pine with heavy understory: 50-150 chains/hr surface fire, "
                "200+ chains/hr wind-driven crown fire. B&B Complex demonstrated sustained "
                "runs of 5,000+ acres/day in extreme conditions. Dense fuel pockets to west "
                "and north ('heavy pockets capable of extreme fire behavior' per CWPP) could "
                "produce fire intensity exceeding suppression capability."
            ),
            "spotting_distance": (
                "1-2 miles in ponderosa crown fire; bark plates and cones are effective "
                "firebrands. Community buildings and cabins — many with wood construction — "
                "are interspersed in forest canopy. FireFree program has improved some "
                "defensible space but forest connectivity remains continuous."
            ),
        },
        "infrastructure_vulnerabilities": {
            "water_system": (
                "Private wells and small community water systems; no municipal water. "
                "Power-dependent pumping. Metolius River spring-fed flow is reliable but "
                "not connected to community fire suppression. No fire hydrant system."
            ),
            "power": (
                "Central Electric Cooperative; overhead lines along Forest Road 14 through "
                "12 miles of forest. Single-corridor power supply. Extended outages during "
                "fire events. No backup generation for most residences."
            ),
            "communications": (
                "Very limited cell coverage; forested canyon terrain blocks signals. "
                "Sisters-Camp Sherman Fire District covers the area. Emergency alerts "
                "dependent on power and cell service — both fail simultaneously during fire events."
            ),
            "medical": (
                "No medical facilities. Nearest clinic in Sisters (15 miles). Nearest hospital "
                "in Bend (35 miles). Single access road means any road closure completely "
                "isolates community from medical care."
            ),
        },
        "demographics_risk_factors": {
            "population": 251,
            "seasonal_variation": (
                "Summer recreation (Metolius River fishing, camping, hiking) can triple "
                "effective population. Resort lodges (Lake Creek Lodge, Metolius River Resort) "
                "bring visitors. USFS campgrounds along Metolius add 500+ seasonal occupants. "
                "Many vacation homes occupied only seasonally."
            ),
            "elderly_percentage": "~30% over 65 (retirement/vacation community)",
            "mobile_homes": (
                "Minimal manufactured housing. Most structures are cabins and single-family homes, "
                "many older wood construction with shake roofs — highly ignitable."
            ),
            "special_needs_facilities": (
                "None. No pharmacy, clinic, or senior services. Community entirely dependent "
                "on Sisters (15 miles) for basic services and Bend (35 miles) for hospital care. "
                "Elderly population with potential mobility limitations in very remote setting."
            ),
        },
    },

    # =========================================================================
    # 7. DETROIT, OR — Beachie Creek Fire, Destroyed 2020
    # =========================================================================
    "detroit_or": {
        "center": [44.7317, -122.1531],
        "terrain_notes": (
            "Detroit (~1,500 ft, though Detroit Lake surface is at ~1,569 ft) is a tiny "
            "mountain community in the North Santiam Canyon, perched on the shore of "
            "Detroit Lake, a 3,580-acre reservoir behind Detroit Dam. The town occupies a "
            "narrow strip of flat land between steep, densely forested canyon walls and the "
            "lake. Highway 22 — a two-lane mountain road — is the sole transportation "
            "corridor through the canyon, passing through Mill City, Gates, Detroit, and "
            "Idanha in sequence. The canyon is deeply incised with slopes rising 2,000-3,000 ft "
            "above the river on both sides, covered in dense Douglas-fir, western hemlock, "
            "and western red cedar. On September 8, 2020, the Beachie Creek Fire — which "
            "had been burning since August 16 in the Opal Creek Wilderness — was driven by "
            "extreme east winds (gusts to 60+ mph) down the canyon, destroying approximately "
            "70% of Detroit's businesses and public buildings in a matter of hours. The town "
            "has been slowly rebuilding but remains profoundly vulnerable due to its canyon "
            "geography and single-road access."
        ),
        "key_features": [
            {"name": "Detroit Lake / Detroit Dam", "bearing": "N-NW", "type": "reservoir",
             "notes": "3,580-acre reservoir; provides partial fire break but lake level drops in late summer, exposing fuel"},
            {"name": "North Santiam River Canyon", "bearing": "E-W corridor", "type": "river_canyon",
             "notes": "Deeply incised canyon; Hwy 22 follows river. Fire channeled through canyon at extreme speed on Sept 8, 2020"},
            {"name": "Opal Creek Wilderness", "bearing": "NE", "type": "wilderness",
             "notes": "35,000 acres of old-growth; Beachie Creek Fire originated here Aug 16, 2020"},
            {"name": "Breitenbush Hot Springs", "bearing": "E", "type": "resort_community",
             "notes": "Remote resort community on Forest Rd 46; destroyed by Beachie Creek Fire. Single-road access."},
            {"name": "Idanha", "bearing": "E (4 miles)", "type": "town",
             "notes": "Tiny community (pop ~135) also devastated by Beachie Creek Fire; shared evacuation corridor"},
            {"name": "Blowout Ridge / Coffin Mountain", "bearing": "S", "type": "ridgeline",
             "notes": "Steep terrain above Detroit; fire raced down these slopes into town"},
        ],
        "elevation_range_ft": [1500, 1700],
        "wui_exposure": "extreme",
        "historical_fires": [
            {"name": "Beachie Creek Fire (Santiam Fire)", "year": 2020, "acres": 193556,
             "details": "Lightning-caused Aug 16, 2020 in Opal Creek Wilderness. During Sept 7-8 Labor Day "
                        "east wind event (60+ mph gusts), merged with Lionshead Fire and raced down North "
                        "Santiam Canyon. Destroyed 1,288 structures total (470 residences, 35 commercial, "
                        "783 other). Nearly wiped out Detroit and Gates — 70% of Detroit's businesses and "
                        "public buildings destroyed. Killed at least 5 people. 40,000 residents evacuated "
                        "across the canyon. Many residents in Gates received no evacuation warning. "
                        "Total suppression cost exceeded $100M."},
            {"name": "Lionshead Fire", "year": 2020, "acres": 204469,
             "details": "Merged with Beachie Creek Fire during Sept 8 wind event; combined fires burned "
                        "nearly 400,000 acres. Started in Mt. Jefferson Wilderness on Aug 16."},
        ],
        "evacuation_routes": [
            {"route": "OR-22 West (toward Salem)", "direction": "W", "lanes": 2,
             "bottleneck": "Two-lane canyon road for 50+ miles through Gates, Mill City to Salem. "
                          "Curving, mountainous terrain with no passing lanes for long stretches.",
             "risk": "Primary evacuation route. During 2020 fire, residents had to drive THROUGH "
                     "active fire zones. Fire burned on both sides of highway. Canyon geometry "
                     "concentrates smoke and heat on road surface."},
            {"route": "OR-22 East (toward Santiam Junction)", "direction": "E", "lanes": 2,
             "bottleneck": "Climbs over Santiam Pass (4,817 ft); connects to US-20. Mountain curves, winter closures.",
             "risk": "Secondary route; during 2020 fire, some residents sent east to Santiam Junction. "
                     "Road passes through continuous forest the entire distance."},
        ],
        "fire_spread_characteristics": {
            "primary_wind_regime": (
                "North Santiam Canyon acts as a massive wind tunnel during east wind events. "
                "September 2020 demonstrated: east winds of 40-60 mph (gusts higher) channeled "
                "through the canyon, pushing the Beachie Creek Fire ~15 miles in a single night. "
                "Downslope (katabatic) winds accelerate fire descent from ridges into the canyon "
                "floor where the town sits. Normal summer pattern is gentle upvalley afternoon winds."
            ),
            "critical_corridors": [
                "North Santiam Canyon — primary fire corridor; wind tunnel effect during east winds",
                "Breitenbush River drainage — secondary fire approach from east/northeast",
                "Steep canyon walls — fire runs downslope at extreme rates into narrow canyon floor",
                "OR-22 highway corridor — only transportation route acts as fire corridor simultaneously",
            ],
            "rate_of_spread_potential": (
                "Beachie Creek Fire demonstrated catastrophic canyon-driven spread: ~15 miles in "
                "12 hours through dense old-growth and second-growth forest. In steep canyon terrain "
                "with wind alignment, rates exceeding 200 chains/hr observed. Upslope runs on canyon "
                "walls can exceed 300 chains/hr. Crown fire conditions virtually continuous in heavy "
                "Douglas-fir stands."
            ),
            "spotting_distance": (
                "2-5 miles during extreme east wind events; massive ember showers documented "
                "during Beachie Creek Fire. Embers crossed Detroit Lake. Dense forest canopy "
                "produces enormous volumes of firebrands during crown fire. Canyon updrafts "
                "loft embers to extreme heights."
            ),
        },
        "infrastructure_vulnerabilities": {
            "water_system": (
                "Municipal water system was largely destroyed in 2020 fire; rebuilt with new "
                "infrastructure. Detroit Dam and reservoir managed by Army Corps. Water intakes "
                "in heavily forested watershed vulnerable to contamination. Post-fire sediment "
                "and debris flows into Detroit Lake have degraded water quality."
            ),
            "power": (
                "Pacific Power; overhead lines through canyon destroyed in 2020 fire. "
                "Restoration took months. Single transmission corridor through canyon means "
                "any fire event causes complete power loss to Detroit, Idanha, and Breitenbush."
            ),
            "communications": (
                "Cell coverage extremely limited in canyon; terrain blocks signals. During 2020 "
                "fire, residents in Gates reported receiving no evacuation alerts — power lines "
                "went down before warnings could be sent. Satellite/landline destroyed. "
                "Marion County 911 had difficulty reaching canyon residents."
            ),
            "medical": (
                "No medical facilities in Detroit. Nearest hospital: Salem Hospital (50 miles west "
                "via Hwy 22). During fire events with road closures, community is completely "
                "isolated from medical care. Air ambulance impossible in smoke conditions."
            ),
        },
        "demographics_risk_factors": {
            "population": 202,
            "seasonal_variation": (
                "Detroit Lake attracts 500,000+ visitors annually for recreation (fishing, "
                "boating, camping). Summer population can exceed 5,000+ on peak weekends — "
                "25x the resident population. Visitors unfamiliar with evacuation routes and "
                "may not be signed up for emergency alerts."
            ),
            "elderly_percentage": "~20% over 65 (many retirees)",
            "mobile_homes": (
                "Minimal post-fire; pre-2020, several RV parks and manufactured homes along "
                "Hwy 22 were destroyed. Rebuilding has been slow due to insurance and permit challenges."
            ),
            "special_needs_facilities": (
                "None in Detroit. Nearest care facilities in Salem. Community has no pharmacy, "
                "no medical clinic, no emergency services beyond volunteer fire department."
            ),
        },
    },

    # =========================================================================
    # 8. GATES, OR — Beachie Creek Fire, Destroyed 2020
    # =========================================================================
    "gates_or": {
        "center": [44.7536, -122.4069],
        "terrain_notes": (
            "Gates (elevation ~950 ft) is a small city 15 miles west of Detroit in the North "
            "Santiam Canyon, situated where the canyon begins to narrow as one travels east "
            "from the broader Willamette Valley. The town sits on a small flat along the North "
            "Santiam River, hemmed in by steep forested slopes. On September 8, 2020, the "
            "Beachie Creek Fire raced through the canyon with extreme east winds, but in Gates, "
            "the primary ignition mechanism was downed power lines — Pacific Power infrastructure "
            "failed in the extreme winds, sparking fires throughout town before the main fire "
            "front arrived. Residents received essentially no evacuation warning. The city was "
            "nearly completely destroyed. The town has been slowly rebuilding but population "
            "has not returned to pre-fire levels. Gates is named for the narrow 'gateway' in "
            "the canyon at this point."
        ),
        "key_features": [
            {"name": "North Santiam River", "bearing": "Through town", "type": "river",
             "notes": "River runs through narrow canyon; provided minimal fire break during 2020 fire"},
            {"name": "Gates Hill / Canyon Walls", "bearing": "N and S", "type": "steep_terrain",
             "notes": "Steep forested slopes rise directly above town on both sides; fire descends from above"},
            {"name": "Mill City", "bearing": "W (3 miles)", "type": "town",
             "notes": "Neighboring city (pop ~1,800) also damaged in 2020 fire; shared evacuation route"},
            {"name": "Pacific Power Line Corridor", "bearing": "E-W through canyon", "type": "utility",
             "notes": "Power lines that failed during east wind event, sparking fires in Gates before main fire front arrived"},
            {"name": "Fath Camp / Camp Upward Bound", "bearing": "Adjacent to town", "type": "camp",
             "notes": "Nearly 50-year-old religious camp destroyed in 2020 fire; still recovering as of 2025"},
        ],
        "elevation_range_ft": [850, 1100],
        "wui_exposure": "extreme",
        "historical_fires": [
            {"name": "Beachie Creek Fire (Santiam Fire)", "year": 2020, "acres": 193556,
             "details": "Gates was devastated: nearly the entire town destroyed. Unlike Detroit where "
                        "the main fire front arrived from the east, Gates was initially ignited by power "
                        "line failures in the extreme east winds before the fire front reached town. "
                        "Residents received NO evacuation notice — power went down, cell service failed, "
                        "and the fire was still 10+ miles away when local ignitions began. Part of the "
                        "1,288-structure total destruction count. Multiple fatalities in the canyon."},
        ],
        "evacuation_routes": [
            {"route": "OR-22 West (toward Stayton/Salem)", "direction": "W", "lanes": 2,
             "bottleneck": "Two-lane canyon road; passes through Mill City and Lyons which were also under evacuation",
             "risk": "Only viable evacuation direction. During 2020, fire burned on both sides of highway. "
                     "Sheriff requested eastbound closure to allow evacuees passage. Canyon road with no alternatives."},
            {"route": "OR-22 East (toward Detroit)", "direction": "E", "lanes": 2,
             "bottleneck": "Leads deeper into canyon toward Detroit, which was also burning",
             "risk": "NOT a viable evacuation route during 2020 event — driving east meant driving into the fire."},
        ],
        "fire_spread_characteristics": {
            "primary_wind_regime": (
                "Canyon funneling of east winds is the critical threat. September 2020 east winds "
                "of 40-60+ mph were amplified through the canyon narrows at Gates. Additionally, "
                "wind-driven power line failures created independent ignition points throughout town "
                "before the main fire front arrived. This dual-ignition mechanism (airborne embers "
                "AND infrastructure failure) is a key lesson from Gates."
            ),
            "critical_corridors": [
                "North Santiam Canyon — wind tunnel from Cascade crest to valley",
                "Power line corridor — infrastructure failure creates ignition sources ahead of fire front",
                "Steep canyon walls — fire descends from above onto canyon floor where town sits",
                "OR-22 road corridor — only access route also serves as fire corridor",
            ],
            "rate_of_spread_potential": (
                "Catastrophic: Beachie Creek Fire covered 15+ miles in the canyon in ~12 hours. "
                "But in Gates, local power-line ignitions destroyed the town even faster than "
                "the main fire front would have. Canyon-channeled winds drove surface and crown "
                "fire at 150-250 chains/hr through mixed conifer forest."
            ),
            "spotting_distance": (
                "2-4 miles with canyon-amplified winds; but the infrastructure-failure ignition "
                "mechanism in Gates effectively created 'spotting' via power lines at distances "
                "of 10+ miles ahead of the fire front."
            ),
        },
        "infrastructure_vulnerabilities": {
            "water_system": (
                "Municipal water system destroyed in 2020 fire; rebuilt as part of recovery. "
                "Small-scale system serving ~500 people. Well and reservoir infrastructure."
            ),
            "power": (
                "Pacific Power overhead lines through canyon — catastrophic failure during 2020 "
                "east wind event. Lines downed by wind and falling trees CAUSED fires in Gates "
                "ahead of the wildfire front. Utility negligence lawsuit filed by residents. "
                "Single-corridor power supply with no redundancy."
            ),
            "communications": (
                "Cell coverage poor in canyon. During 2020 fire, communication failure was total — "
                "no evacuation warnings reached residents. Power failure eliminated landlines "
                "and cell tower backup power insufficient. This was a primary factor in "
                "near-total town destruction."
            ),
            "medical": (
                "No medical facilities. Nearest hospital: Santiam Hospital in Stayton (25 miles west) "
                "or Salem Hospital (45 miles west). During road closures, completely isolated."
            ),
        },
        "demographics_risk_factors": {
            "population": 471,
            "seasonal_variation": (
                "Some increase from Detroit Lake recreation traffic passing through on Hwy 22. "
                "Summer cabins and vacation properties. Population has not returned to pre-fire "
                "levels; many displaced residents did not rebuild."
            ),
            "elderly_percentage": "~22% over 65",
            "mobile_homes": (
                "Pre-fire: significant manufactured home presence along highway corridor. "
                "Most were destroyed in 2020 fire. Rebuilt housing is primarily stick-built "
                "with improved fire resistance."
            ),
            "special_needs_facilities": (
                "None. No pharmacy, no clinic, no senior center. Community entirely dependent "
                "on services in Stayton, Salem, or Bend."
            ),
        },
    },

    # =========================================================================
    # 6. KLAMATH FALLS, OR — Bootleg Fire Region, High Desert
    # =========================================================================
    "klamath_falls_or": {
        "center": [42.2249, -121.7817],
        "terrain_notes": (
            "Klamath Falls (4,094 ft) occupies the southeastern shore of Upper Klamath Lake, "
            "Oregon's largest natural freshwater lake, in a high-desert basin surrounded by "
            "mountains. The Klamath Mountains rise to the west with rugged volcanic formations "
            "and mixed conifer forest. To the east, the terrain transitions through rolling "
            "juniper hills to the Fremont-Winema National Forest where the 2021 Bootleg Fire "
            "burned 413,765 acres. The city sits in a broad, relatively flat basin with the "
            "Klamath River running south toward California. The surrounding landscape is a "
            "complex mosaic of irrigated agricultural land (reclamation project), sagebrush "
            "steppe, juniper woodland, and mixed conifer forest — creating varied fire behavior "
            "potential. The high-desert climate features hot, dry summers with frequent lightning "
            "and significant diurnal temperature swings."
        ),
        "key_features": [
            {"name": "Upper Klamath Lake", "bearing": "NW", "type": "lake",
             "notes": "Oregon's largest natural lake; provides some fire buffer on NW side of city"},
            {"name": "Fremont-Winema National Forest", "bearing": "NE and E", "type": "national_forest",
             "notes": "2.2 million acres; Bootleg Fire (413,765 acres) burned in this forest in 2021"},
            {"name": "Klamath River Canyon", "bearing": "S", "type": "river_canyon",
             "notes": "River corridor toward California; channeled winds and fire corridor"},
            {"name": "Oregon Institute of Technology", "bearing": "W edge of city", "type": "campus",
             "notes": "University campus on hilltop; could serve as emergency staging area"},
            {"name": "California-Oregon Intertie", "bearing": "NE", "type": "power_transmission",
             "notes": "500kV transmission corridor; Bootleg Fire burned 8+ miles of corridor, threatened 15 more"},
            {"name": "Stukel Mountain / Hogback Mountain", "bearing": "SE-S", "type": "mountain_terrain",
             "notes": "Forested volcanic ridges south of city; fire can descend slopes toward developed areas"},
        ],
        "elevation_range_ft": [4094, 5000],
        "wui_exposure": "high",
        "historical_fires": [
            {"name": "Bootleg Fire", "year": 2021, "acres": 413765,
             "details": "Third-largest fire in Oregon history. Started July 6 near Beatty, 30 miles NE "
                        "of Klamath Falls. Burned for 6+ weeks in Fremont-Winema NF. Grew at 1,000 acres/hr "
                        "at peak. Destroyed 408 buildings (161 houses, 247 outbuildings). Threatened 3,000 homes. "
                        "2,200+ personnel deployed. Burned 8 miles of California-Oregon Intertie power corridor. "
                        "Created its own weather (pyrocumulonimbus clouds)."},
            {"name": "Klamathon Fire", "year": 2018, "acres": 38000,
             "details": "Burned along OR-CA border in Klamath River canyon; threatened Hornbrook, CA. "
                        "Demonstrated cross-border fire risk and Klamath River corridor spread potential."},
            {"name": "Substation Fire", "year": 2018, "acres": 77000,
             "details": "Grass fire east of The Dalles; burned at extreme rates in grass/wheat. "
                        "Part of broader Klamath Basin fire risk pattern."},
        ],
        "evacuation_routes": [
            {"route": "US-97 North (toward Chemult/Bend)", "direction": "N", "lanes": 2,
             "bottleneck": "Two-lane highway through forest and rangeland for 60+ miles; fire can close segments",
             "risk": "Long corridor through fire-prone landscape; Bootleg Fire threatened nearby segments"},
            {"route": "US-97 South (toward Weed, CA)", "direction": "S", "lanes": 2,
             "bottleneck": "Climbs through forested terrain to California border; traffic backs up at state line",
             "risk": "Klamath River canyon fire risk; 2018 Klamathon Fire burned along this corridor"},
            {"route": "OR-39 (toward Merrill/Tulelake)", "direction": "SE", "lanes": 2,
             "bottleneck": "Rural two-lane through agricultural land; limited services for 40+ miles",
             "risk": "Grass and brush fire risk; relatively good evacuation route in agricultural terrain"},
            {"route": "OR-140 (toward Lakeview)", "direction": "E", "lanes": 2,
             "bottleneck": "Remote highway through high desert; minimal services for 100+ miles",
             "risk": "Passes through Fremont-Winema NF and Bootleg Fire burn scar; debris flow risk"},
        ],
        "fire_spread_characteristics": {
            "primary_wind_regime": (
                "Prevailing SW winds from the Sacramento Valley encounter Klamath Mountains, "
                "creating complex terrain-driven wind patterns. Strong diurnal thermal cycles "
                "in the high-desert basin. Summer afternoon thunderstorms produce dry lightning — "
                "primary ignition source. East wind events less pronounced than western Oregon "
                "but still drive critical fire weather."
            ),
            "critical_corridors": [
                "Fremont-Winema NF to city — NE approach through mixed conifer and juniper",
                "Klamath River canyon — channeled winds carry fire S toward California",
                "California-Oregon Intertie power corridor — cleared corridor can carry grass fire",
                "Upper Klamath Lake margins — dry grasslands and tule marshes seasonally flammable",
            ],
            "rate_of_spread_potential": (
                "Bootleg Fire demonstrated extreme spread at 1,000 acres/hr under peak conditions. "
                "In juniper/sagebrush near city: 50-150 chains/hr. In grass/wheat: 200-400 chains/hr. "
                "Mixed conifer in mountains: 30-80 chains/hr surface, 150+ chains/hr crown fire. "
                "Drought conditions amplify all rates significantly."
            ),
            "spotting_distance": (
                "Bootleg Fire created pyrocumulonimbus clouds capable of long-range spotting (3-5+ miles). "
                "In juniper near city: 0.25-0.5 mile spotting. Grass fires rely on continuous "
                "spread rather than spotting. Mixed conifer: 1-2 mile spotting in crown fire."
            ),
        },
        "infrastructure_vulnerabilities": {
            "water_system": (
                "City water from Upper Klamath Lake treatment plant and groundwater wells. "
                "Aging infrastructure in some neighborhoods. Agricultural water diversions "
                "(Klamath Reclamation Project) can conflict with firefighting water needs."
            ),
            "power": (
                "Pacific Power; California-Oregon Intertie 500kV transmission serves California load. "
                "Bootleg Fire burned 8 miles of this corridor and threatened to cut power to California. "
                "Local distribution through juniper and forest corridors vulnerable to fire."
            ),
            "communications": (
                "Klamath County 911; cell towers on ridge tops. Basin terrain provides adequate "
                "coverage in city but dead zones in surrounding mountains and forest. "
                "Emergency radio repeaters on mountain sites vulnerable to fire."
            ),
            "medical": (
                "Sky Lakes Medical Center — 176 beds, only hospital in Klamath County. "
                "Nearest alternatives: Medford (75 miles NW) or Redding, CA (200 miles S). "
                "Limited surge capacity for mass-casualty events. Oregon Tech EMS training center."
            ),
        },
        "demographics_risk_factors": {
            "population": 22174,
            "seasonal_variation": (
                "Moderate tourism to Crater Lake (60 miles NW), Upper Klamath Lake, and "
                "Klamath Wildlife Refuges. Seasonal agricultural workers for potato and "
                "cattle operations. Winter snowbird population minimal."
            ),
            "elderly_percentage": "~16% over 65",
            "mobile_homes": (
                "Moderate manufactured home presence, particularly in south and east side "
                "of city and unincorporated county. Estimated 10-12% of housing stock."
            ),
            "special_needs_facilities": (
                "Crystal Terrace Assisted Living; several adult foster homes. "
                "Sky Lakes Medical Center limited capacity. Oregon Institute of Technology "
                "campus population (~5,000) during academic year."
            ),
        },
    },

    # =========================================================================
    # 4. LA PINE, OR — Embedded in Deschutes National Forest
    # =========================================================================
    "la_pine_or": {
        "center": [43.6801, -121.5039],
        "terrain_notes": (
            "La Pine (4,236 ft) is a small city literally embedded within Deschutes National "
            "Forest, approximately 30 miles south of Bend along US-97. The community is a "
            "loose collection of homes and businesses strung along the highway corridor, "
            "surrounded on all sides by lodgepole and ponderosa pine forest. The Little "
            "Deschutes River and Fall River run through the area, creating riparian corridors "
            "in otherwise continuous coniferous forest. Much of the surrounding forest has "
            "heavy fuel loading from decades of fire suppression and bark beetle mortality. "
            "The greater La Pine area (~20,000 residents in unincorporated Deschutes County) "
            "sprawls through forest with no clear urban boundary — homes are scattered among "
            "trees on large lots with minimal defensible space. Volcanic pumice soils support "
            "lodgepole pine monocultures highly susceptible to stand-replacing fire."
        ),
        "key_features": [
            {"name": "Deschutes National Forest", "bearing": "All directions", "type": "national_forest",
             "notes": "1.6 million acre forest completely surrounds community; continuous canopy fuel"},
            {"name": "Newberry Volcanic Monument", "bearing": "E", "type": "volcanic_terrain",
             "notes": "Paulina Peak (7,985 ft) and volcanic terrain east of town; unique fire behavior in lava flows"},
            {"name": "Little Deschutes River", "bearing": "E of US-97", "type": "riparian_corridor",
             "notes": "Meandering river with grass meadows and riparian vegetation creating fire corridor"},
            {"name": "La Pine State Park", "bearing": "N", "type": "recreation",
             "notes": "Popular campground in forest; seasonal visitors in fire-prone setting"},
            {"name": "Wickiup Reservoir / Crane Prairie", "bearing": "W", "type": "reservoir",
             "notes": "Irrigation reservoirs in forested area; recreation areas with limited egress"},
            {"name": "US-97 Corridor", "bearing": "N-S", "type": "highway",
             "notes": "Primary transportation artery; fire can close highway isolating community"},
        ],
        "elevation_range_ft": [4100, 4500],
        "wui_exposure": "extreme",
        "historical_fires": [
            {"name": "Darlene 3 Fire", "year": 2024, "acres": 3900,
             "details": "Exploded to life in Deschutes NF just outside La Pine; over 1,100 buildings "
                        "threatened, 1,000+ homes on evacuation alert. Governor declared emergency conflagration."},
            {"name": "Jackpine Fire", "year": 2024, "acres": 50,
             "details": "Fire on Masten Road led to Level 2 evacuations and 4-mile closure of US-97 south "
                        "of La Pine. Demonstrated how quickly fire can threaten highway lifeline."},
            {"name": "McKay Butte Fire", "year": 2024, "acres": 190,
             "details": "Grew from 90 to 190 acres overnight east of La Pine in lodgepole pine."},
            {"name": "Davis Fire", "year": 2003, "acres": 21000,
             "details": "Large fire in Deschutes NF south of La Pine; demonstrated scale of potential fire events."},
        ],
        "evacuation_routes": [
            {"route": "US-97 North (toward Bend)", "direction": "N", "lanes": 2,
             "bottleneck": "Two-lane highway through continuous forest for 30 miles to Bend; shared with Sunriver evacuees",
             "risk": "Primary escape route; 2024 Jackpine Fire closed 4-mile segment. Fire on either side traps corridor."},
            {"route": "US-97 South (toward Chemult/Klamath)", "direction": "S", "lanes": 2,
             "bottleneck": "Remote two-lane highway through lodgepole forest; 70 miles to Klamath Falls",
             "risk": "Long drive through heavy forest with no services; fire can close multiple segments simultaneously."},
            {"route": "County Roads East (Newberry area)", "direction": "E", "lanes": 2,
             "bottleneck": "Narrow rural roads through forest; dead ends at volcanic terrain",
             "risk": "Not viable evacuation routes; lead deeper into forest and volcanic landscape."},
            {"route": "Forest Roads West (Cascade Lakes)", "direction": "W", "lanes": 2,
             "bottleneck": "Seasonal, unpaved forest roads; not suitable for mass evacuation",
             "risk": "Dead-end roads to reservoirs and trailheads; could become fire traps."},
        ],
        "fire_spread_characteristics": {
            "primary_wind_regime": (
                "Afternoon SW thermal winds in summer drive fire from Cascade slopes toward "
                "community. East wind events push fire rapidly across flat lodgepole terrain. "
                "Diurnal drainage flows from Newberry Crater create nighttime wind shifts. "
                "Relatively flat terrain allows fire to spread in any wind direction."
            ),
            "critical_corridors": [
                "US-97 highway corridor — fire can race along road margins through continuous forest",
                "Little Deschutes River — riparian and grass fuel corridor through developed areas",
                "Lodgepole pine flats — uniform fuel allows unimpeded fire spread across landscape",
                "Fall River corridor — drainage connects Cascade highlands to community",
            ],
            "rate_of_spread_potential": (
                "In lodgepole pine with grass understory: 40-100 chains/hr surface fire, "
                "crown fire runs of 200-400 chains/hr possible in bark beetle-killed stands. "
                "Darlene 3 Fire grew explosively to 3,900 acres. Flat terrain with uniform fuel "
                "allows sustained high-rate spread with minimal terrain friction."
            ),
            "spotting_distance": (
                "0.5-1 mile in lodgepole pine; less spotting than ponderosa due to smaller bark "
                "plates, but crown fire ember showers can ignite multiple spots simultaneously. "
                "Pumice soil creates dry litter beds highly receptive to ember ignition."
            ),
        },
        "infrastructure_vulnerabilities": {
            "water_system": (
                "Municipal water from groundwater wells; limited storage capacity. "
                "Power-dependent pumping system vulnerable to outages. Rural areas "
                "on private wells with no fire flow capability."
            ),
            "power": (
                "Central Electric Cooperative and Pacific Power; long overhead transmission "
                "lines through forest. Extended outages during fire events. No local generation."
            ),
            "communications": (
                "Limited cell coverage in surrounding forest. Deschutes County 911 dispatch. "
                "Emergency alerts depend on cell/internet connectivity that degrades during fire events."
            ),
            "medical": (
                "No hospital; La Pine Community Health Center for basic care. Nearest hospital "
                "is St. Charles Bend (30 miles north). Air ambulance from Bend; smoke conditions "
                "can ground helicopters during fire events."
            ),
        },
        "demographics_risk_factors": {
            "population": 2566,
            "seasonal_variation": (
                "Greater La Pine area ~20,000 including unincorporated Deschutes County. "
                "Summer recreation (Cascade Lakes, Newberry Crater) adds thousands of visitors. "
                "Many vacation homes occupied only seasonally — owners may not receive alerts."
            ),
            "elderly_percentage": "~25% over 65",
            "mobile_homes": (
                "Significant manufactured home presence in unincorporated areas; many on large "
                "forested lots with poor defensible space. Estimated 15-20% of housing stock."
            ),
            "special_needs_facilities": (
                "Limited; one senior center. Nearest hospital and emergency services 30 miles "
                "away in Bend. Large elderly population with limited mobility."
            ),
        },
    },

    # =========================================================================
    # 2. MEDFORD / ASHLAND, OR — Rogue Valley, Almeda Fire Corridor
    # =========================================================================
    "medford_ashland_or": {
        "center": [42.3265, -122.8756],
        "terrain_notes": (
            "Medford (1,382 ft) and Ashland (1,949 ft) anchor the Rogue Valley / Bear Creek "
            "Valley in southern Oregon, a 100+ square-mile alluvial basin bounded by the "
            "Siskiyou Mountains to the south, Cascade foothills to the east, and Rogue River "
            "canyon to the north. The Bear Creek corridor (I-5 / OR-99 alignment) is the "
            "primary urban-wildland interface — the 2020 Almeda Fire proved this corridor "
            "can carry fire 9 miles through continuous urban development. Ashland sits in "
            "a narrowing valley at the base of the Siskiyous with steep, forested slopes "
            "rising immediately above the city. Medford occupies the broader valley floor "
            "with irrigated agriculture and orchards (cherry, pear) creating seasonal fuel "
            "variability. The Bear Creek Greenway provides a continuous riparian fuel corridor "
            "connecting all communities from Ashland through Talent, Phoenix, and into Medford."
        ),
        "key_features": [
            {"name": "Bear Creek Greenway", "bearing": "N-S corridor", "type": "riparian_corridor",
             "notes": "26-mile paved path along Bear Creek; riparian vegetation created continuous fuel for Almeda Fire's 9-mile run"},
            {"name": "Ashland Watershed / Siskiyou Slopes", "bearing": "S of Ashland", "type": "steep_terrain",
             "notes": "Steep forested slopes rising 3,000+ ft above city; Ashland Creek drainage feeds directly into downtown"},
            {"name": "Table Rock", "bearing": "N of Medford", "type": "volcanic_mesa",
             "notes": "Prominent volcanic plateau; grassland fire risk in surrounding plains"},
            {"name": "Rogue River / Gold Hill Corridor", "bearing": "NW", "type": "river_canyon",
             "notes": "Deep river canyon with thermal wind effects; fire can race through canyon terrain"},
            {"name": "I-5 / OR-99 Transportation Corridor", "bearing": "N-S", "type": "infrastructure",
             "notes": "Interstate and parallel highway through Bear Creek Valley; Almeda Fire crossed and paralleled both"},
            {"name": "Emigrant Lake", "bearing": "SE of Ashland", "type": "reservoir",
             "notes": "Irrigation reservoir surrounded by grass and oak savanna; seasonal drawdown exposes dry fuel"},
        ],
        "elevation_range_ft": [1300, 2200],
        "wui_exposure": "extreme",
        "historical_fires": [
            {"name": "Almeda Fire", "year": 2020, "acres": 3200,
             "details": "September 8 Labor Day fire; human-caused, started in field near Almeda Dr in Ashland. "
                        "Wind-driven (40+ mph gusts from south) 9-mile run through Bear Creek corridor. "
                        "Destroyed 2,800+ structures (including ~1,600 manufactured homes in 18 mobile home "
                        "parks), killed 3 people. Most destructive wildfire in Oregon recorded history. "
                        "Primarily urban interface fire — burned through Talent, Phoenix, and into south Medford."},
            {"name": "Angora Fire (South Ashland)", "year": 2009, "acres": 100,
             "details": "Burned on steep slopes above Ashland; demonstrated vulnerability of Siskiyou foothill interface."},
        ],
        "evacuation_routes": [
            {"route": "I-5", "direction": "N-S", "lanes": 4,
             "bottleneck": "Siskiyou Pass (S) and Sexton Mtn (N) are steep, winding segments with truck slowdowns",
             "risk": "Only interstate through valley; Almeda Fire paralleled I-5 for 9 miles, fire crossed highway at multiple points"},
            {"route": "OR-99 (Pacific Highway)", "direction": "N-S", "lanes": 2,
             "bottleneck": "Parallel to I-5 through Bear Creek Valley; passes directly through fire-destroyed areas",
             "risk": "Alternative to I-5 but passes through same fire corridor; 2020 fire closed both simultaneously"},
            {"route": "OR-66 (Green Springs Hwy)", "direction": "E from Ashland", "lanes": 2,
             "bottleneck": "Winding mountain road over Green Springs summit (4,551 ft); very limited capacity",
             "risk": "Only eastern escape from Ashland; climbs through dense forest with extreme fire risk"},
            {"route": "OR-62 (Crater Lake Hwy)", "direction": "NE from Medford", "lanes": 2,
             "bottleneck": "Traffic backs up at White City / Agate Desert during evacuations",
             "risk": "Route passes through mixed forest/grassland; brush fire risk in Table Rock area"},
        ],
        "fire_spread_characteristics": {
            "primary_wind_regime": (
                "Rogue Valley channeling effect amplifies wind through the Bear Creek corridor. "
                "During 2020 Almeda Fire, anomalous strong southerly winds (40+ mph) pushed fire "
                "northward through corridor. Normal summer pattern is afternoon NW winds with "
                "thermal upvalley flow. Critical fire weather occurs with offshore (east) events "
                "or strong pressure-gradient winds from the south."
            ),
            "critical_corridors": [
                "Bear Creek riparian corridor — continuous fuel from Ashland to Medford (9+ miles)",
                "I-5 / OR-99 highway margins — grass, brush, and homeless camp fuel accumulation",
                "Ashland Creek drainage — steep, forested canyon directly above downtown Ashland",
                "Griffin Creek / Wagner Creek drainages — fire pathways from wildlands into developed areas",
            ],
            "rate_of_spread_potential": (
                "Almeda Fire demonstrated urban-corridor spread of ~2 mph sustained through "
                "mixed residential/commercial/riparian fuel. In grasslands on valley floor, "
                "rates of 100-300 chains/hr possible. Slope-driven fires on Siskiyou foothills "
                "above Ashland can achieve 50-100 chains/hr upslope."
            ),
            "spotting_distance": (
                "0.25-0.5 miles in Bear Creek corridor; ember transport from structure fires "
                "and riparian vegetation. Almeda Fire spot fires ignited across I-5. "
                "On Siskiyou slopes, 1-2 mile spotting possible from crown fires in mixed conifer."
            ),
        },
        "infrastructure_vulnerabilities": {
            "water_system": (
                "Medford: Duff Water Treatment Plant on Big Butte Creek pipeline. "
                "Ashland: Ashland Creek watershed (forested, fire-vulnerable). "
                "TAP (Talent-Ashland-Phoenix) water system serves 23,000 people; Almeda Fire "
                "damaged water infrastructure, contaminated lines with benzene from melted "
                "plastic service laterals. Boil-water advisories lasted weeks post-fire."
            ),
            "power": (
                "Pacific Power serves valley; overhead distribution through fire-prone corridors. "
                "Almeda Fire destroyed numerous transformers and poles along Bear Creek. "
                "Power restoration took weeks in destroyed areas."
            ),
            "communications": (
                "Jackson County Emergency alert system had significant gaps during Almeda Fire — "
                "many residents in Talent and Phoenix never received evacuation notices. "
                "Language barriers (large Spanish-speaking population) compounded alert failures."
            ),
            "medical": (
                "Asante Rogue Regional Medical Center (378 beds, Level II Trauma) in Medford; "
                "Providence Medford Medical Center (120 beds). Serves 600,000+ people across "
                "9 counties in southern Oregon and northern California. Surge capacity concern "
                "during regional fire events."
            ),
        },
        "demographics_risk_factors": {
            "population": 113000,
            "seasonal_variation": (
                "Oregon Shakespeare Festival brings 400,000+ visitors to Ashland annually "
                "(Feb-Nov). Summer tourism peaks coincide with fire season. Agricultural "
                "workers (seasonal) increase valley population during harvest."
            ),
            "elderly_percentage": "~18% over 65 (higher in Ashland ~22%)",
            "mobile_homes": (
                "Critical vulnerability: Almeda Fire destroyed ~1,600 manufactured homes in "
                "18 mobile home parks. 65% of homes lost were in mobile home parks. "
                "Many parks housed predominantly Latino families. Pre-fire, ~15% of Talent "
                "and Phoenix housing was manufactured homes."
            ),
            "special_needs_facilities": (
                "Multiple assisted living facilities in Medford; Ashland has retirement "
                "communities. Rogue Valley Manor (continuing care). Spanish-speaking population "
                "in Talent/Phoenix had limited access to English-only emergency alerts."
            ),
        },
    },

    # =========================================================================
    # 12. OAKRIDGE, OR — Middle Fork Willamette, Extreme Isolation Risk
    # =========================================================================
    "oakridge_or": {
        "center": [43.7465, -122.4612],
        "terrain_notes": (
            "Oakridge (~1,200-1,600 ft) is an isolated former timber town on the Middle Fork "
            "of the Willamette River, surrounded by the Willamette National Forest. Located "
            "approximately 40 miles east of Eugene on Oregon Route 58, the city sits in a "
            "narrow valley at the confluence of Salmon Creek, Salt Creek, Hills Creek, and "
            "the Middle and North Forks of the Willamette. Dense Douglas-fir and western hemlock "
            "forest rises steeply on all sides. Highway 58 — the primary route between Eugene "
            "and Central Oregon — is the city's lifeline and sole realistic evacuation route. "
            "Oakridge has experienced recurrent fire threats: the 2023 Bedrock Fire, 2024 "
            "Willamette Complex (Oakridge Lightning Fires), and 2025 Aubrey Mountain and "
            "Dunning Road fires all triggered evacuations and highway closures. The town has "
            "a high poverty rate (30%), significant elderly population, and 25% manufactured "
            "housing — creating a highly vulnerable demographic profile."
        ),
        "key_features": [
            {"name": "Middle Fork Willamette River", "bearing": "E-W through town", "type": "river_corridor",
             "notes": "River corridor connects deep forest to town; riparian fuel continuous upstream"},
            {"name": "Hills Creek Reservoir", "bearing": "SE", "type": "reservoir",
             "notes": "Large reservoir upstream; forested watershed above. Dam downstream of town."},
            {"name": "OR-58 (Willamette Highway)", "bearing": "E-W", "type": "highway",
             "notes": "Only highway through area; repeatedly closed by fires (2023, 2024, 2025). Sole evacuation route."},
            {"name": "Salmon Creek / Salt Creek", "bearing": "S", "type": "drainages",
             "notes": "Steep forested drainages converging on town; fire corridors from Cascade foothills"},
            {"name": "Westfir", "bearing": "W (adjacent)", "type": "town",
             "notes": "Tiny neighbor community (pop ~250) at confluence of North Fork Willamette; shares fire risk and evacuation"},
            {"name": "Willamette National Forest", "bearing": "All directions", "type": "national_forest",
             "notes": "1.68 million acres of dense forest completely surrounds community; heavy fuel loading"},
        ],
        "elevation_range_ft": [1200, 1600],
        "wui_exposure": "extreme",
        "historical_fires": [
            {"name": "Aubrey Mountain Fire", "year": 2025, "acres": 35,
             "details": "East of Oakridge off Hwy 58 on Middle Fork Ranger District. Triggered Level 3 "
                        "'Go Now' evacuations for east Oakridge. Highway 58 partially closed. Steep, "
                        "timber terrain. 65% contained before downgrade."},
            {"name": "Dunning Road Fire", "year": 2025, "acres": 100,
             "details": "Prompted evacuation orders for east Oakridge and partial Highway 58 closure. "
                        "Burned in timber on steep terrain."},
            {"name": "Willamette Complex (Oakridge Lightning Fires)", "year": 2024, "acres": 5000,
             "details": "Multiple lightning-caused fires 8-22 miles from Oakridge. Level 2 evacuations "
                        "for Oakridge and Westfir. Demonstrated pattern of recurrent fire threat."},
            {"name": "Bedrock Fire", "year": 2023, "acres": 200,
             "details": "Fall Creek area on Middle Fork District. Active near town."},
            {"name": "Tumblebug Fire", "year": 2009, "acres": 4000,
             "details": "Burned on Middle Fork Ranger District; dead snags from this fire created "
                        "increased fuel loading for subsequent fires."},
        ],
        "evacuation_routes": [
            {"route": "OR-58 West (toward Eugene/Springfield)", "direction": "W", "lanes": 2,
             "bottleneck": "Two-lane highway through narrow Willamette valley for 40 miles to Eugene. "
                          "Passes through forested corridor with fire risk the entire distance.",
             "risk": "Sole primary evacuation route. Repeatedly closed by fires (2023-2025). When Hwy 58 "
                     "closes, Oakridge is effectively stranded with no viable alternative route."},
            {"route": "OR-58 East (toward Willamette Pass/US-97)", "direction": "E", "lanes": 2,
             "bottleneck": "Climbs to Willamette Pass (5,128 ft); mountain road through dense forest",
             "risk": "Secondary route; leads deeper into forest. Passes through areas of recurrent fire. "
                     "Connects to US-97 at Chemult (65 miles). Winter closures."},
            {"route": "Forest Roads", "direction": "N/S", "lanes": 1,
             "bottleneck": "Unpaved forest roads; not suitable for passenger vehicles or mass evacuation",
             "risk": "Dead-end forest roads leading to trailheads; potential fire traps."},
        ],
        "fire_spread_characteristics": {
            "primary_wind_regime": (
                "Valley funneling effect concentrates winds along the Middle Fork Willamette "
                "and OR-58 corridor. East wind events push fire from Cascades down the valley "
                "toward town. Afternoon upvalley thermal winds in summer can push fire eastward "
                "into surrounding forest. Multiple tributary drainages create complex wind "
                "interactions. Heavy fuel loading from bark beetle mortality and previous fire "
                "snags amplify fire behavior."
            ),
            "critical_corridors": [
                "Middle Fork Willamette valley — primary fire corridor; wind channeling during east wind events",
                "Salmon Creek and Salt Creek drainages — fire pathways from Cascade foothills into town",
                "OR-58 highway corridor — fire can race along road through continuous forest; sole escape route",
                "Previous burn scars (Tumblebug 2009) — heavy snag loading creates extreme fire behavior zones",
            ],
            "rate_of_spread_potential": (
                "In dense Douglas-fir/hemlock forest on steep slopes: 50-150 chains/hr surface fire, "
                "200-300 chains/hr crown fire runs. Previous burn scars with heavy snag loading "
                "create unpredictable fire behavior — snag fall, spot fires, and jackpot burning. "
                "Continuous fuel from forest floor to canopy enables rapid transition to crown fire."
            ),
            "spotting_distance": (
                "1-3 miles in steep terrain with strong updrafts from canyon walls. Dense "
                "Douglas-fir canopy produces massive ember showers during crown fire. "
                "Valley geometry concentrates embers in the narrow corridor where town sits."
            ),
        },
        "infrastructure_vulnerabilities": {
            "water_system": (
                "Small municipal water system; vulnerable to contamination from fire in surrounding "
                "watershed. Limited storage capacity. Power-dependent pumping."
            ),
            "power": (
                "Lane Electric Cooperative; overhead lines through forested canyon. "
                "Fire-related outages common and extended. Single transmission corridor "
                "means any fire event can black out the community."
            ),
            "communications": (
                "Limited cell coverage in valley and surrounding forest. Lane County 911. "
                "Emergency alerts depend on power and cell service, both vulnerable during fire. "
                "Remote location means delayed emergency response."
            ),
            "medical": (
                "No hospital. Small community health clinic. Nearest hospital: PeaceHealth "
                "Sacred Heart at RiverBend in Springfield (40 miles west). During Hwy 58 closure, "
                "community is completely isolated from hospital care. Air ambulance grounded by smoke."
            ),
        },
        "demographics_risk_factors": {
            "population": 3206,
            "seasonal_variation": (
                "Mountain biking tourism (Oakridge is known as 'Mountain Biking Capital of Oregon') "
                "and camping/fishing bring summer visitors. Some seasonal timber workers. "
                "Population relatively stable year-round."
            ),
            "elderly_percentage": "~22% over 65",
            "mobile_homes": (
                "25.4% of housing is manufactured homes — one of the highest rates in Oregon. "
                "Many on forested lots with poor defensible space. Aging housing stock "
                "(median construction year 1959). Critical vulnerability."
            ),
            "special_needs_facilities": (
                "Very limited. No pharmacy in town as of recent years. Senior center. "
                "Poverty rate ~30%, median household income ~$35,000. Limited transportation "
                "for elderly and disabled. Environmental justice concern — isolated, low-income "
                "community with extreme fire risk."
            ),
        },
    },

    # =========================================================================
    # 11. PHOENIX, OR — Almeda Fire, Devastated 2020
    # =========================================================================
    "phoenix_or": {
        "center": [42.2751, -122.8178],
        "terrain_notes": (
            "Phoenix (1,560 ft) is a small city in the Rogue Valley immediately north of "
            "Talent and south of Medford, straddling I-5 and OR-99 along the Bear Creek "
            "corridor. Like Talent, Phoenix was devastated by the 2020 Almeda Fire, which "
            "burned through the Bear Creek Greenway and destroyed hundreds of homes and "
            "businesses. The town occupies a flat valley position with Bear Creek and the "
            "Greenway running through its eastern side. Phoenix has a significant Latino "
            "population and had numerous mobile home parks that were particularly vulnerable. "
            "The city's fire exposure comes primarily from the urban-interface corridor along "
            "Bear Creek rather than traditional wildland fire, though grass-covered hills "
            "rise to the west. Recovery has been ongoing for 5+ years with new housing and "
            "infrastructure emerging."
        ),
        "key_features": [
            {"name": "Bear Creek / Greenway", "bearing": "N-S through east side", "type": "riparian_corridor",
             "notes": "Carried the Almeda Fire through town; riparian vegetation was continuous fuel"},
            {"name": "I-5 / OR-99 / CORP Railroad", "bearing": "N-S", "type": "transportation",
             "notes": "Transportation infrastructure through town; fire burned along all corridors"},
            {"name": "Mobile Home Parks", "bearing": "Along OR-99 and Bear Creek", "type": "residential",
             "notes": "Multiple manufactured home communities destroyed; housed predominantly Latino families"},
            {"name": "Phoenix Commercial District", "bearing": "Central on OR-99", "type": "commercial",
             "notes": "Businesses along OR-99 destroyed in Almeda Fire; some still rebuilding as of 2025"},
        ],
        "elevation_range_ft": [1500, 1700],
        "wui_exposure": "high",
        "historical_fires": [
            {"name": "Almeda Fire", "year": 2020, "acres": 3200,
             "details": "September 8, 2020; fire burned through Phoenix as part of the 9-mile corridor "
                        "from Ashland to south Medford. Hundreds of homes and businesses destroyed. "
                        "Part of the 2,800+ structure total. Mobile home parks particularly devastated. "
                        "Latino families disproportionately affected. Recovery continues 5+ years later."},
        ],
        "evacuation_routes": [
            {"route": "I-5 North (toward Medford)", "direction": "N", "lanes": 4,
             "bottleneck": "Best capacity route but fire burned along and crossed I-5",
             "risk": "Fire paralleled I-5; however northward movement was viable as fire pushed from south"},
            {"route": "I-5 South (toward Talent/Ashland)", "direction": "S", "lanes": 4,
             "bottleneck": "Fire origin direction; not viable for southbound evacuation",
             "risk": "Fire was approaching from this direction during Almeda Fire"},
            {"route": "Fern Valley Road / Local Streets West", "direction": "W", "lanes": 2,
             "bottleneck": "Local roads to western hills; limited capacity",
             "risk": "Leads to rural foothill areas; not designed for mass evacuation"},
        ],
        "fire_spread_characteristics": {
            "primary_wind_regime": (
                "Same as Talent — anomalous strong southerly winds during Almeda Fire pushed "
                "fire through Bear Creek corridor. Rogue Valley channeling amplifies wind. "
                "Normal summer: afternoon NW winds, thermal upvalley flow."
            ),
            "critical_corridors": [
                "Bear Creek riparian corridor — continuous fuel connecting Talent through Phoenix to Medford",
                "I-5 / OR-99 margins — grass, brush, and structure-to-structure spread corridor",
                "Mobile home park corridors — tight spacing enabled rapid structure-to-structure fire spread",
            ],
            "rate_of_spread_potential": (
                "Consistent with Almeda Fire observations: ~2 mph sustained urban-corridor spread. "
                "Structure-to-structure in mobile home parks: minutes. Riparian corridor: 50-100 chains/hr."
            ),
            "spotting_distance": (
                "0.25-0.5 miles from structure fires and wind-driven embers. Propane tanks "
                "and vehicle fuel tanks added to ember generation and spotting."
            ),
        },
        "infrastructure_vulnerabilities": {
            "water_system": (
                "TAP (Talent-Ashland-Phoenix) shared water system; same vulnerability as Talent. "
                "Benzene contamination from melted plastic pipes post-fire."
            ),
            "power": (
                "Pacific Power; overhead distribution destroyed in fire corridor. "
                "Extensive rebuilding of electrical infrastructure ongoing."
            ),
            "communications": (
                "Same Jackson County alert system failures as Talent — many Phoenix residents "
                "received no warning. Spanish-speaking population particularly underserved by "
                "English-only alert systems."
            ),
            "medical": (
                "No hospital; served by Medford hospitals 5-8 miles north. During Almeda Fire, "
                "road access to Medford was compromised by smoke and fire along I-5."
            ),
        },
        "demographics_risk_factors": {
            "population": 4475,
            "seasonal_variation": "Minimal; primarily year-round resident community.",
            "elderly_percentage": "~18% over 65",
            "mobile_homes": (
                "Pre-fire: significant manufactured home population, predominantly housing "
                "Latino families. Majority of homes lost were manufactured. Post-fire recovery "
                "includes new manufactured home communities with improved fire resilience."
            ),
            "special_needs_facilities": (
                "Limited. Phoenix-Talent School District. Significant ESL community requiring "
                "bilingual emergency services. Environmental justice concerns — fire "
                "disproportionately impacted lower-income communities of color."
            ),
        },
    },

    # =========================================================================
    # 3. SISTERS, OR — Cascade Foothills, Ponderosa Pine WUI
    # =========================================================================
    "sisters_or": {
        "center": [44.2910, -121.5494],
        "terrain_notes": (
            "Sisters (3,187 ft) sits at the eastern base of the Cascade Range where "
            "ponderosa pine forest meets high-desert juniper woodland. The town is surrounded "
            "by Deschutes National Forest on three sides (west, north, south). Named for "
            "the Three Sisters volcanic peaks visible to the west, the community occupies "
            "a narrow band of development along the US-20/OR-126 corridor. The landscape "
            "is dominated by fire-adapted ponderosa pine with significant standing dead "
            "timber from bark beetle kill. Whychus Creek (formerly Squaw Creek) runs south "
            "of town through a forested canyon. Black Butte (6,436 ft) rises prominently "
            "to the northwest. Nearly 20 large fires have threatened the greater Sisters "
            "area since 1994, making it one of Oregon's most fire-threatened communities. "
            "In 2025, Sisters passed a wildfire code for new development — one of the first "
            "in Oregon."
        ),
        "key_features": [
            {"name": "Three Sisters Wilderness", "bearing": "W", "type": "wilderness",
             "notes": "242,000-acre wilderness; source of major fires including B&B Complex. No suppression until fire threatens boundary."},
            {"name": "Black Butte", "bearing": "NW", "type": "volcanic_peak",
             "notes": "6,436 ft cinder cone; fire lookout tower. Pine forests on slopes are continuous fuel to town."},
            {"name": "Whychus Creek Canyon", "bearing": "S of town", "type": "drainage_corridor",
             "notes": "Forested canyon corridor that could channel fire and wind toward town from the southwest"},
            {"name": "Indian Ford Meadow / Sage Steppe", "bearing": "E-NE", "type": "grassland_transition",
             "notes": "Transition zone to high desert; grass fires can spread rapidly and ignite adjacent pine stands"},
            {"name": "Camp Sherman / Metolius Basin", "bearing": "NW (10 mi)", "type": "forest_community",
             "notes": "Nearby community in dense forest; shares fire district and evacuation infrastructure"},
            {"name": "McKenzie Pass (OR-242)", "bearing": "W", "type": "mountain_pass",
             "notes": "Seasonal road through lava fields and dense forest; closed Oct-June. Emergency egress only in summer."},
        ],
        "elevation_range_ft": [3100, 3400],
        "wui_exposure": "extreme",
        "historical_fires": [
            {"name": "B&B Complex Fire", "year": 2003, "acres": 90769,
             "details": "Linked pair of lightning-caused fires in central Cascades west of Sisters. "
                        "Burned 90,769 acres Aug-Sep 2003, destroyed 13 structures, cost $38.7M to suppress. "
                        "Eastern side burned through ponderosa and lodgepole pine. Camp Sherman evacuated (~300 people). "
                        "Changed national perception of fire management in Pacific Northwest."},
            {"name": "Black Crater Fire", "year": 2006, "acres": 9300,
             "details": "Burned west of Sisters near Black Crater. Threatened Sisters and Camp Sherman. "
                        "Demonstrated ongoing risk from Cascade fires approaching town."},
            {"name": "Green Ridge Fire", "year": 2020, "acres": 1000,
             "details": "During Labor Day wind event; forced evacuation notices for Camp Sherman area. "
                        "Grew rapidly in east winds before weather moderated."},
            {"name": "Link Fire", "year": 2003, "acres": 400,
             "details": "Small fire near Sisters demonstrating ignition potential in local ponderosa stands."},
        ],
        "evacuation_routes": [
            {"route": "US-20 East (toward Bend)", "direction": "E", "lanes": 2,
             "bottleneck": "Two-lane highway; 20 miles to Bend through forested corridor",
             "risk": "Primary evacuation route; shared with Camp Sherman evacuees. Fire can cut this route."},
            {"route": "US-20/OR-22 West (Santiam Pass)", "direction": "W", "lanes": 2,
             "bottleneck": "Mountain pass (4,817 ft); winter closures. Winding through dense forest.",
             "risk": "Passes through burn scars and heavy forest; B&B Complex fire threatened this corridor."},
            {"route": "OR-126 South (toward Redmond)", "direction": "SE", "lanes": 2,
             "bottleneck": "Shared corridor with US-20 through Sisters then diverges south",
             "risk": "Only connects after reaching US-20; does not provide independent evacuation route from town center."},
            {"route": "OR-242 (McKenzie Pass)", "direction": "W", "lanes": 2,
             "bottleneck": "Seasonal road, closed October-June. Very narrow, winding, no shoulders.",
             "risk": "Summer-only escape route through lava fields and dense forest; not viable for mass evacuation."},
        ],
        "fire_spread_characteristics": {
            "primary_wind_regime": (
                "Dominant summer afternoon SW winds push fires from Cascades toward town. "
                "During east wind events (like September 2020), fires in Cascade forests can "
                "be pushed rapidly westward, but town is more protected from east-origin fires. "
                "Thermal belt effects on surrounding buttes create complex local wind patterns."
            ),
            "critical_corridors": [
                "Cascades-to-town corridor via Whychus Creek — channeled wind and continuous forest fuel",
                "Black Butte / Green Ridge approach from NW — dense ponderosa connects wildlands to town",
                "Indian Ford corridor from NE — grass fire transition to pine interface",
                "US-20 highway corridor — fire can travel along road margins through continuous forest",
            ],
            "rate_of_spread_potential": (
                "In ponderosa pine stands with grass understory: 30-80 chains/hr surface fire, "
                "200+ chains/hr with wind-driven crown runs. B&B Complex demonstrated multi-day "
                "runs of 5,000+ acres/day in extreme conditions. Bark beetle-killed stands "
                "dramatically increase crown fire potential."
            ),
            "spotting_distance": (
                "1-2 miles in ponderosa pine crown fires; extensive ember production from "
                "bark and cone material. Shake and wood-sided structures in town center "
                "highly vulnerable to ember ignition."
            ),
        },
        "infrastructure_vulnerabilities": {
            "water_system": (
                "City water from 4 wells with 1.6 million gallon reservoir; approximately "
                "32 miles of distribution mains and 1,500 active connections. Well-based "
                "system requires electrical power for pumping; extended power outages "
                "compromise water supply and fire suppression capacity."
            ),
            "power": (
                "Central Electric Cooperative; overhead distribution lines through forested "
                "corridors. Power outages during fire events common. No local generation backup."
            ),
            "communications": (
                "Deschutes County 911 dispatch. Cell coverage adequate in town but degrades "
                "rapidly in surrounding forest. Sisters-Camp Sherman Fire District covers "
                "large rural area with limited stations."
            ),
            "medical": (
                "No hospital in Sisters; nearest is St. Charles Bend (22 miles east). "
                "Sisters has one small medical clinic. Fire evacuation medical needs must "
                "route to Bend or Redmond. Air ambulance dependent on smokefree conditions."
            ),
        },
        "demographics_risk_factors": {
            "population": 3738,
            "seasonal_variation": (
                "Tourism and events (Sisters Outdoor Quilt Show, rodeo, music festivals) can "
                "triple effective population on peak weekends. Vacation rentals and summer "
                "homes add ~2,000 seasonal residents. Camp Sherman adds ~300 permanent / "
                "500 seasonal residents to the fire district."
            ),
            "elderly_percentage": "~25% over 65 (retirement destination)",
            "mobile_homes": (
                "Limited manufactured housing within city limits; more common in "
                "surrounding unincorporated Deschutes County areas."
            ),
            "special_needs_facilities": (
                "Sisters Senior Living; limited assisted-care capacity. Remote location "
                "means extended EMS response times to Bend hospitals."
            ),
        },
    },

    # =========================================================================
    # 13. SUNRIVER, OR — Resort Community in Deschutes NF
    # =========================================================================
    "sunriver_or": {
        "center": [43.8834, -121.4371],
        "terrain_notes": (
            "Sunriver (~4,164 ft) is a master-planned resort community approximately 15 miles "
            "south of Bend, entirely surrounded by Deschutes National Forest ponderosa pine "
            "forest. Originally a WWII military training camp (Camp Abbot, 1943), the community "
            "was developed as a resort in 1968 and now features ~4,600 homes, a lodge, golf "
            "courses, an airstrip (S21), and extensive recreation facilities. The community is "
            "built within the forest — large ponderosa pines stand in yards and line every "
            "street. The Deschutes River runs along the western boundary. Despite the resort "
            "character, approximately 2,000 people live year-round, with the effective population "
            "swelling to 10,000-30,000 during summer weekends and holidays. The community has "
            "invested significantly in wildfire preparedness through its Community Wildfire "
            "Protection Plan (CWPP) and prescribed burning programs, but the fundamental "
            "vulnerability of thousands of structures embedded in continuous forest remains."
        ),
        "key_features": [
            {"name": "Deschutes National Forest", "bearing": "All directions", "type": "national_forest",
             "notes": "1.6 million acres surrounds community; continuous ponderosa pine forest to boundary"},
            {"name": "Deschutes River", "bearing": "W boundary", "type": "river",
             "notes": "Runs along west side; provides partial fire break but riparian vegetation is fuel"},
            {"name": "Sunriver Airport (S21)", "bearing": "N end", "type": "airport",
             "notes": "3,600 ft paved runway; emergency aircraft access but smoke can close the field"},
            {"name": "Mt. Bachelor", "bearing": "W (15 miles)", "type": "volcanic_peak",
             "notes": "Ski area in national forest; Bachelor Complex Fire (2024) threatened Sunriver from this direction"},
            {"name": "SHARC Recreation Center", "bearing": "Central", "type": "recreation",
             "notes": "$18M aquatic center; potential emergency shelter. 1.4 million visitors in first 5 years."},
            {"name": "Spring River / Fall River", "bearing": "S", "type": "natural_springs",
             "notes": "Spring-fed rivers in forested areas south of resort; fire corridors from south"},
        ],
        "elevation_range_ft": [4100, 4250],
        "wui_exposure": "extreme",
        "historical_fires": [
            {"name": "Bachelor Complex (Little Lava Fire)", "year": 2024, "acres": 2500,
             "details": "Largest fire in Bachelor Complex; threatened Sunriver directly. Level 2 'Get Set' "
                        "evacuation notices issued for Sunriver borders. Multiple fires in Deschutes NF "
                        "threatened community from W and SW."},
            {"name": "Darlene 3 Fire", "year": 2024, "acres": 3900,
             "details": "Burned in Deschutes NF near La Pine; over 1,000 homes on evacuation alert. "
                        "Close proximity to Sunriver demonstrated regional fire exposure."},
            {"name": "Sunriver vicinity fires", "year": 2020, "acres": 100,
             "details": "Multiple small fires during Labor Day east wind event; increased monitoring but "
                        "community was spared direct impact."},
        ],
        "evacuation_routes": [
            {"route": "South Century Drive to US-97", "direction": "N toward Bend", "lanes": 2,
             "bottleneck": "Single access road from resort to US-97; 4,600 homes funneling through limited exits",
             "risk": "Primary evacuation route; passes through national forest. If fire cuts S Century Drive, "
                     "community could be trapped. 10,000-30,000 summer visitors create massive evacuation demand."},
            {"route": "Sunriver-to-La Pine via US-97 South", "direction": "S", "lanes": 2,
             "bottleneck": "Two-lane highway through continuous forest; La Pine also evacuating",
             "risk": "Secondary route south; shared with La Pine evacuees. Forest on both sides of highway."},
            {"route": "Forest Service Roads", "direction": "W", "lanes": 1,
             "bottleneck": "Unpaved forest roads; not suitable for mass evacuation of resort",
             "risk": "Emergency-only routes into forest; potential fire traps rather than evacuation routes."},
        ],
        "fire_spread_characteristics": {
            "primary_wind_regime": (
                "Summer afternoon SW winds push fires from Cascade foothills toward community. "
                "East wind events drive fires across flat pine terrain toward the Cascades. "
                "Relatively flat topography allows fire to approach from any direction. "
                "Diurnal thermal patterns create complex wind shifts. Resort is nestled in "
                "the forest with no significant wind breaks."
            ),
            "critical_corridors": [
                "Deschutes River corridor — fire spread pathway along western boundary",
                "South Century Drive / US-97 — evacuation route also serves as fire corridor",
                "Mt. Bachelor / Cascade Lakes area — fire approaches from SW through continuous forest",
                "La Pine direction — fire can approach from south through lodgepole/ponderosa",
            ],
            "rate_of_spread_potential": (
                "In ponderosa pine with grass understory: 50-150 chains/hr surface fire, "
                "200+ chains/hr with wind-driven crown runs. Within the resort, structure-to-"
                "structure spread possible due to tree canopy connecting homes. Well-maintained "
                "defensible space in core resort helps but edges are most vulnerable."
            ),
            "spotting_distance": (
                "0.5-1.5 miles in ponderosa; large bark plates produce firebrands. "
                "Many homes have wood shake roofs (older construction) highly vulnerable "
                "to ember ignition. CWPP has identified this as priority for mitigation."
            ),
        },
        "infrastructure_vulnerabilities": {
            "water_system": (
                "Sunriver Utilities Company provides water from groundwater wells. Adequate "
                "for normal operations but fire flow demand during a community-wide event "
                "would overwhelm capacity. Power-dependent pumping."
            ),
            "power": (
                "Central Electric Cooperative and Midstate Electric Cooperative; overhead "
                "lines through forest. Fire-related outages can be extended. Limited backup "
                "generation for critical facilities."
            ),
            "communications": (
                "Cell coverage good within resort; degrades in surrounding forest. "
                "Deschutes County emergency alerts functional. Sunriver has internal "
                "communication systems (owner association notifications)."
            ),
            "medical": (
                "Sunriver has a small urgent care clinic (seasonal). No hospital; nearest is "
                "St. Charles Bend (20 miles north). During mass evacuation, medical transport "
                "competes with evacuee traffic on same roads."
            ),
        },
        "demographics_risk_factors": {
            "population": 2023,
            "seasonal_variation": (
                "EXTREME seasonal variation: year-round population ~2,000 but summer weekends "
                "can exceed 30,000 (vacation rentals, resort guests, day visitors). Peak fire "
                "season coincides exactly with peak occupancy. Many visitors unfamiliar with "
                "evacuation routes, not registered for alerts, and may not speak English."
            ),
            "elderly_percentage": "~40-50% over 65 (median age 70.1 — retirement community)",
            "mobile_homes": "Minimal; resort community with primarily permanent single-family structures.",
            "special_needs_facilities": (
                "Extremely elderly population (median age 70.1). Multiple residents with mobility "
                "limitations. No hospital or emergency medical facilities in community. "
                "K-8 school in community; children present during school year."
            ),
        },
    },

    # =========================================================================
    # 10. TALENT, OR — Almeda Fire, 700+ Homes Destroyed 2020
    # =========================================================================
    "talent_or": {
        "center": [42.2457, -122.7887],
        "terrain_notes": (
            "Talent (1,635 ft) is a small city in the Rogue Valley of southern Oregon, located "
            "along Interstate 5 and Oregon Route 99 between Ashland (to the south) and Phoenix "
            "(to the north). The city occupies the flat Bear Creek Valley floor, bounded by Bear "
            "Creek to the east and the low hills of the Rogue Valley to the west. Talent was "
            "one of the two communities most devastated by the 2020 Almeda Fire, which destroyed "
            "approximately one-third of the town — 700+ homes, predominantly in mobile home parks "
            "housing lower-income and Latino families. The fire ran through the Bear Creek riparian "
            "corridor and along the I-5/OR-99 transportation corridor, burning through 18 mobile "
            "home parks between Ashland and south Medford. Talent has since emerged as a national "
            "model for wildfire recovery, with new energy-efficient housing and community-owned "
            "mobile home parks replacing destroyed stock."
        ),
        "key_features": [
            {"name": "Bear Creek / Bear Creek Greenway", "bearing": "N-S through east side of town", "type": "riparian_corridor",
             "notes": "Riparian corridor that carried the Almeda Fire; continuous fuel from Ashland to Medford"},
            {"name": "I-5 / OR-99 Corridor", "bearing": "N-S", "type": "transportation",
             "notes": "Interstate and parallel highway bracket town; fire crossed and paralleled both"},
            {"name": "Mobile Home Parks (multiple)", "bearing": "Along OR-99 and Bear Creek", "type": "residential",
             "notes": "18 mobile home parks between Ashland and Medford were destroyed; Talent lost 700+ homes, "
                      "65% were manufactured homes. Talent Mobile Estates (now Talent Community Cooperative) was devastated."},
            {"name": "Wagner Creek", "bearing": "W", "type": "drainage",
             "notes": "Tributary to Bear Creek draining western hills; secondary fire pathway"},
            {"name": "Talent City Park / Schools", "bearing": "Central", "type": "infrastructure",
             "notes": "Community facilities that served as gathering points during and after fire"},
        ],
        "elevation_range_ft": [1550, 1750],
        "wui_exposure": "high",
        "historical_fires": [
            {"name": "Almeda Fire", "year": 2020, "acres": 3200,
             "details": "September 8, 2020; human-caused fire started in field on Almeda Dr in north Ashland. "
                        "Driven by 40+ mph winds, burned 9 miles through Bear Creek corridor. Talent lost "
                        "700+ homes — approximately one-third of the town. 65% of homes lost valley-wide "
                        "were manufactured homes. 3 fatalities total. Most destructive fire in Oregon "
                        "history. Jackson County alert system failures meant many Talent residents received "
                        "no evacuation warning. Large Spanish-speaking population had no Spanish-language alerts. "
                        "Town has become nationally recognized leader in wildfire resilience and recovery."},
        ],
        "evacuation_routes": [
            {"route": "I-5 North (toward Medford)", "direction": "N", "lanes": 4,
             "bottleneck": "Interstate provides good capacity but fire burned along and crossed I-5",
             "risk": "Almeda Fire paralleled I-5 for 9 miles; evacuees had to flee through smoke and flames on highway"},
            {"route": "I-5 South (toward Ashland)", "direction": "S", "lanes": 4,
             "bottleneck": "Fire originated in this direction; driving south meant driving toward fire origin",
             "risk": "Not viable during Almeda Fire — fire was pushing north FROM Ashland direction"},
            {"route": "OR-99 (Pacific Highway)", "direction": "N-S", "lanes": 2,
             "bottleneck": "Parallel to I-5 through destroyed areas; significantly less capacity than I-5",
             "risk": "Fire burned through OR-99 corridor; road impassable during active fire"},
            {"route": "Talent Avenue / Local Streets West", "direction": "W", "lanes": 2,
             "bottleneck": "Local roads to western hills; limited capacity, lead to rural areas",
             "risk": "Limited capacity escape to western hills; not a primary evacuation route"},
        ],
        "fire_spread_characteristics": {
            "primary_wind_regime": (
                "During the Almeda Fire, anomalous strong southerly winds (40+ mph gusts) pushed "
                "the fire northward through the Bear Creek corridor. Normal summer pattern is "
                "afternoon NW winds with thermal upvalley flow. The fire burned primarily through "
                "urban/suburban fuel — structures, vehicles, landscaping, riparian vegetation — "
                "rather than wildland fuel, making it an unprecedented urban-interface event."
            ),
            "critical_corridors": [
                "Bear Creek riparian corridor — continuous fuel connecting all Rogue Valley communities",
                "I-5 / OR-99 highway margins — grass, brush, and structure-to-structure fire spread",
                "Mobile home park corridors — extremely tight spacing allowed structure-to-structure spread",
                "Wagner Creek drainage — secondary fire pathway from wildlands to developed areas",
            ],
            "rate_of_spread_potential": (
                "Almeda Fire demonstrated sustained urban-corridor spread of ~2 mph over 9 miles. "
                "Structure-to-structure spread in mobile home parks was rapid — minutes between "
                "ignition and full involvement. Riparian vegetation along Bear Creek burned at "
                "50-100 chains/hr. Grass along highway margins: 200+ chains/hr."
            ),
            "spotting_distance": (
                "0.25-0.5 miles via ember transport from burning structures and vegetation. "
                "Wind-driven embers from mobile home fires ignited adjacent structures rapidly. "
                "Propane tanks and vehicle fuel added to ember generation."
            ),
        },
        "infrastructure_vulnerabilities": {
            "water_system": (
                "TAP (Talent-Ashland-Phoenix) water system serves ~23,000 people. Fire damaged "
                "water infrastructure; melted plastic service laterals contaminated water with "
                "benzene. Boil-water advisories for weeks post-fire. Water pressure dropped "
                "during fire, hampering suppression efforts."
            ),
            "power": (
                "Pacific Power; overhead distribution destroyed through fire corridor. "
                "Power restoration took weeks in destroyed areas. Lack of power hampered "
                "pumping for water system recovery."
            ),
            "communications": (
                "Jackson County emergency alert system had critical gaps — many Talent "
                "residents received NO evacuation warning. Language barriers: large "
                "Spanish-speaking population had no access to Spanish-language emergency "
                "alerts. Cell towers functional but alert system failure was the primary issue."
            ),
            "medical": (
                "No hospital in Talent; served by Asante Rogue Regional (378 beds) and "
                "Providence Medford Medical Center (120 beds), both in Medford, 10 miles north. "
                "During fire, roads to Medford were compromised."
            ),
        },
        "demographics_risk_factors": {
            "population": 6282,
            "seasonal_variation": (
                "Minimal seasonal variation; primarily year-round residents. Agricultural "
                "workers in the Rogue Valley (orchards, vineyards) add to population during harvest."
            ),
            "elderly_percentage": "~23% over 65",
            "mobile_homes": (
                "CRITICAL VULNERABILITY: 65% of homes destroyed valley-wide were manufactured homes. "
                "Talent lost 700+ homes, predominantly in mobile home parks. Pre-fire ~15% of housing "
                "was manufactured. Many parks housed Latino families. Post-fire, Talent Community "
                "Cooperative (resident-owned) replaced destroyed Talent Mobile Estates with ~80 new "
                "energy-efficient manufactured homes (Energy Trust partnership)."
            ),
            "special_needs_facilities": (
                "Limited; small senior housing. Large ESL population requiring multilingual "
                "emergency services. Phoenix-Talent School District serves the area. "
                "Post-fire Gateway housing project provided student housing for displaced families."
            ),
        },
    },

    # =========================================================================
    # 5. THE DALLES, OR — Columbia Gorge, Eagle Creek Fire Area
    # =========================================================================
    "the_dalles_or": {
        "center": [45.5946, -121.1787],
        "terrain_notes": (
            "The Dalles (elevation ~100-500 ft along the Columbia River, rising to 1,500+ ft "
            "on the benchlands) is the largest city on the Oregon side of the Columbia River "
            "outside the Portland metro area. Situated at the eastern gateway to the Columbia "
            "River Gorge, the terrain transitions dramatically from the wet, forested western "
            "Gorge to the dry, grassland-covered eastern Gorge. The city occupies a series "
            "of terraces and benchlands rising steeply from the Columbia River. Cherry orchards "
            "and dry grasslands surround the city on the south and east. The Columbia River "
            "Gorge creates a massive natural wind tunnel, with persistent strong winds from "
            "the west in summer and periodic powerful east winds in fall/winter. The city was "
            "affected by smoke and fallout from the 2017 Eagle Creek Fire (50,000 acres) in "
            "the western Gorge, and the surrounding terrain of grass and scattered oak presents "
            "significant fire risk during the dry summer months."
        ),
        "key_features": [
            {"name": "Columbia River Gorge", "bearing": "W", "type": "river_canyon",
             "notes": "80-mile canyon creates extreme wind tunnel effect; 2017 Eagle Creek Fire demonstrated Gorge fire risk"},
            {"name": "The Dalles Dam / Lake Celilo", "bearing": "E", "type": "dam_reservoir",
             "notes": "Federal dam and reservoir; infrastructure requiring fire protection"},
            {"name": "Cherry Orchards / Agricultural Lands", "bearing": "S and SE", "type": "agricultural",
             "notes": "Irrigated orchards and dry grasslands create mosaic fuel pattern; grass fires common"},
            {"name": "Chenoweth Creek Drainage", "bearing": "S", "type": "drainage",
             "notes": "Creek corridor rising into dry grass and oak woodland; fire pathway into residential areas"},
            {"name": "Mill Creek Watershed", "bearing": "S-SW", "type": "watershed",
             "notes": "Municipal watershed in forested terrain; fire threatens water supply"},
            {"name": "I-84 / Columbia River Corridor", "bearing": "E-W", "type": "transportation",
             "notes": "Interstate and BNSF Railway along river; Eagle Creek Fire closed I-84 for weeks"},
        ],
        "elevation_range_ft": [100, 1700],
        "wui_exposure": "high",
        "historical_fires": [
            {"name": "Eagle Creek Fire", "year": 2017, "acres": 50000,
             "details": "Burned 50,000 acres in Columbia River Gorge; caused by teenager with fireworks. "
                        "Burned for 3 months. Closed I-84 for extended periods, forced hundreds of evacuations. "
                        "Subsequent debris flows (268 landslides) from atmospheric rivers hitting burn scar. "
                        "Dense Douglas-fir/western hemlock forest in steep terrain created extreme fire behavior."},
            {"name": "Sevenmile Hill Fire", "year": 2015, "acres": 2100,
             "details": "Grass and brush fire south of The Dalles; threatened homes on benchlands above city."},
            {"name": "Mosier Creek Fire", "year": 2020, "acres": 200,
             "details": "During Labor Day east wind event; burned near Mosier, 15 miles west of The Dalles. "
                        "Level 3 evacuations issued."},
        ],
        "evacuation_routes": [
            {"route": "I-84 West (toward Portland)", "direction": "W", "lanes": 4,
             "bottleneck": "Gorge section with rockfall zones and narrow segments; Eagle Creek Fire closed this for weeks",
             "risk": "Fire in Gorge closes primary east-west route; detour adds 100+ miles via US-97/I-90"},
            {"route": "I-84 East (toward Biggs Junction)", "direction": "E", "lanes": 4,
             "bottleneck": "Open terrain but grass fire risk along highway margins",
             "risk": "Best evacuation direction during Gorge fires; connects to US-97 N-S corridor"},
            {"route": "US-197 South (toward Dufur/Maupin)", "direction": "S", "lanes": 2,
             "bottleneck": "Climbs steeply out of river valley; winding two-lane road through grass and wheat lands",
             "risk": "Grass fires can cut road; limited capacity for mass evacuation. Connects to US-97."},
            {"route": "US-30 (Historic Columbia River Hwy)", "direction": "W", "lanes": 2,
             "bottleneck": "Narrow, scenic road not suitable for mass evacuation",
             "risk": "Parallels I-84 but through more forested terrain; higher fire risk than interstate."},
        ],
        "fire_spread_characteristics": {
            "primary_wind_regime": (
                "Columbia Gorge wind tunnel effect dominates: strong westerly winds in summer "
                "(20-40 mph sustained), periodic powerful easterly winds in fall (40-60+ mph). "
                "East wind events are the primary fire weather concern — drive fires westward "
                "through Gorge and can fan grass fires near The Dalles. The 2017 Eagle Creek "
                "Fire was pushed by east winds. Thermal effects from steep canyon walls create "
                "unpredictable local wind patterns."
            ),
            "critical_corridors": [
                "Columbia River Gorge — extreme wind-driven fire corridor with steep terrain",
                "Chenoweth Creek drainage — fire pathway from grass/oak uplands into city",
                "Mill Creek watershed — forested corridor connecting wildlands to water supply",
                "I-84 highway corridor margins — grass and brush fuel along transportation lifeline",
            ],
            "rate_of_spread_potential": (
                "Extremely fast in grass: 200-400 chains/hr with Gorge winds. In forested "
                "Gorge terrain, crown fire runs of 50-100 chains/hr on steep slopes. "
                "Eagle Creek Fire burned ~50,000 acres total with multi-day high-intensity runs. "
                "Post-fire debris flow risk adds secondary hazard."
            ),
            "spotting_distance": (
                "Gorge winds can carry embers 1-3 miles in steep terrain with strong updrafts. "
                "Eagle Creek Fire generated spot fires across the Columbia River into Washington. "
                "In grass near The Dalles, spotting less significant but rate of spread compensates."
            ),
        },
        "infrastructure_vulnerabilities": {
            "water_system": (
                "5 deep wells (15-25% of supply), 7 storage reservoirs, 100 miles of water mains, "
                "5,083 connections, 700+ fire hydrants, 16 pressure zones. New aquifer storage and "
                "recovery (ASR) system increases capacity. Mill Creek watershed fire could contaminate "
                "surface water intakes. Google data centers have driven $28M in new water infrastructure."
            ),
            "power": (
                "Northern Wasco County PUD; overhead lines through Gorge subject to wind damage and fire. "
                "Bonneville Power Administration high-voltage transmission through Gorge; Eagle Creek "
                "Fire threatened transmission corridors."
            ),
            "communications": (
                "Wasco County 911; cell towers on bluffs above city. Gorge winds can damage towers. "
                "Emergency alert systems functional but Gorge terrain creates coverage shadows."
            ),
            "medical": (
                "Mid-Columbia Medical Center — 49-bed community hospital. Limited capacity for "
                "mass-casualty events. Nearest Level II trauma center is in Portland (85 miles west) "
                "or Bend (130 miles south) — both routes can be closed by fire."
            ),
        },
        "demographics_risk_factors": {
            "population": 16010,
            "seasonal_variation": (
                "Cherry harvest (June-August) brings seasonal agricultural workers. "
                "Gorge tourism and wind sports attract visitors year-round. "
                "Google data center employees add to daytime population."
            ),
            "elderly_percentage": "~18% over 65",
            "mobile_homes": (
                "Moderate manufactured home presence, particularly on south-side benchlands "
                "and in unincorporated Wasco County. Estimated 8-10% of housing stock."
            ),
            "special_needs_facilities": (
                "Flagstone Senior Living; Orchard View Estates. Mid-Columbia Medical Center "
                "limited capacity. Long transport times to major trauma centers."
            ),
        },
    },

    # =========================================================================
    # 15. HOOD RIVER, OR — Columbia Gorge Wind Corridor Town
    # =========================================================================
    "hood_river_or": {
        "center": [45.7054, -121.5215],
        "terrain_notes": (
            "Hood River sits on the south bank of the Columbia River at the heart of "
            "the Columbia River Gorge. The Gorge is the only sea-level passage through "
            "the Cascade Range, creating a massive natural wind tunnel. Elevation ranges "
            "from 60 ft at the river to 4,000+ ft on the upper valley slopes toward "
            "Mt. Hood. The town is Oregon's premier windsurfing/kiteboarding destination "
            "because of its persistent strong winds. During east wind events (typically "
            "fall/winter), winds can exceed 60 mph through the Gorge, creating extreme "
            "fire weather. The upper Hood River Valley transitions into orchards and "
            "then dense conifer forest approaching Mt. Hood."
        ),
        "key_features": [
            {"name": "Columbia River Gorge", "bearing": "E-W", "type": "river_canyon",
             "notes": "Gap wind corridor; sustained winds 30-60 mph common during east events"},
            {"name": "Hood River Valley", "bearing": "S", "type": "valley",
             "notes": "Orchards transition to forest; funnels east winds toward Mt. Hood"},
            {"name": "Mt. Hood Foothills", "bearing": "S-SW", "type": "mountain",
             "notes": "Dense conifer forest; recreation access via OR-35"},
        ],
        "elevation_range_ft": [60, 4200],
        "wui_exposure": "high",
        "historical_fires": [
            {"name": "Eagle Creek Fire", "year": 2017, "acres": 50000,
             "details": "Major Gorge fire 15 miles west; closed I-84 for weeks, heavy smoke impact."},
            {"name": "Dollar Lake Fire", "year": 2011, "acres": 6200,
             "details": "Lightning-caused fire on Mt. Hood NF; threatened upper valley communities."},
        ],
        "evacuation_routes": [
            {"route": "I-84 East", "direction": "E", "lanes": 4,
             "bottleneck": "Gorge narrows at Mosier, rockfall zones",
             "risk": "Gorge fires can close I-84 in both directions"},
            {"route": "I-84 West", "direction": "W", "lanes": 4,
             "bottleneck": "Tunnel and viaduct sections west of town",
             "risk": "Primary Portland corridor; fire or slide closure strands town"},
            {"route": "OR-35 South", "direction": "S", "lanes": 2,
             "bottleneck": "Mountain highway to Mt. Hood; seasonal closures",
             "risk": "Only southern escape; through forest fire-prone terrain"},
        ],
        "fire_spread_characteristics": {
            "primary_wind_regime": "Strong westerlies in summer, extreme easterlies in fall/winter",
            "critical_corridors": ["Gorge gap wind corridor", "Hood River Valley drainage"],
            "rate_of_spread_potential": "Extreme in grass during Gorge wind events; 200+ chains/hr",
            "spotting_distance": "1-2 miles in Gorge wind events",
        },
    },

    # =========================================================================
    # 16. MOSIER, OR — Small Gorge Community
    # =========================================================================
    "mosier_or": {
        "center": [45.6837, -121.3997],
        "terrain_notes": (
            "Mosier is a small unincorporated community (pop ~500) between Hood River "
            "and The Dalles in the dry eastern Columbia Gorge. Surrounded by grass and "
            "oak savanna on steep slopes rising from the river. The Mosier Creek Fire "
            "(2020) during Labor Day east winds forced Level 3 evacuations."
        ),
        "key_features": [
            {"name": "Mosier Creek Canyon", "bearing": "S", "type": "drainage",
             "notes": "Steep canyon with grass and oak; fire pathway into town"},
            {"name": "Rowena Crest", "bearing": "W", "type": "cliff",
             "notes": "Dramatic Gorge cliffs with east wind acceleration zone"},
        ],
        "elevation_range_ft": [100, 1500],
        "wui_exposure": "extreme",
        "historical_fires": [
            {"name": "Mosier Creek Fire", "year": 2020, "acres": 200,
             "details": "Labor Day east wind event; Level 3 evacuations for entire community."},
        ],
        "evacuation_routes": [
            {"route": "I-84 East/West", "direction": "E-W", "lanes": 4,
             "bottleneck": "Single access point from town to interstate",
             "risk": "Grass fire can cut access road to I-84"},
        ],
        "fire_spread_characteristics": {
            "primary_wind_regime": "Gorge gap winds; extreme east events",
            "critical_corridors": ["Mosier Creek drainage", "Gorge cliffs"],
            "rate_of_spread_potential": "Very high in grass; 200+ chains/hr",
            "spotting_distance": "0.5-1 mile in east wind events",
        },
    },

    # =========================================================================
    # 17. MAUPIN, OR — Deschutes Canyon Grassland
    # =========================================================================
    "maupin_or": {
        "center": [45.1754, -121.0795],
        "terrain_notes": (
            "Maupin (pop ~430) sits in the Deschutes River canyon surrounded by "
            "grass and juniper rangeland. Hot, dry summers with frequent grass fires. "
            "The Deschutes River canyon creates terrain-channeled winds. Limited fire "
            "suppression resources in this remote area."
        ),
        "key_features": [
            {"name": "Deschutes River Canyon", "bearing": "N-S through town", "type": "river_canyon",
             "notes": "Deep canyon channels wind; rafting/recreation brings fire risk"},
            {"name": "White River Canyon", "bearing": "W", "type": "side_canyon",
             "notes": "Tributary canyon connecting to wheat/grasslands"},
        ],
        "elevation_range_ft": [1000, 2500],
        "wui_exposure": "high",
        "historical_fires": [
            {"name": "Multiple grass fires", "year": 2018, "acres": 5000,
             "details": "Recurring large grass fires in surrounding rangeland during summer."},
        ],
        "evacuation_routes": [
            {"route": "US-197 North", "direction": "N", "lanes": 2,
             "bottleneck": "Canyon road; limited passing",
             "risk": "Grass fire can close highway corridor"},
            {"route": "US-197 South", "direction": "S", "lanes": 2,
             "bottleneck": "Climbs out of canyon through grassland",
             "risk": "Same highway, grass fire risk"},
        ],
        "fire_spread_characteristics": {
            "primary_wind_regime": "Canyon-channeled winds; thermal upslope afternoon",
            "critical_corridors": ["Deschutes canyon N-S", "White River side canyon"],
            "rate_of_spread_potential": "Extreme in grass; 300+ chains/hr in wind events",
            "spotting_distance": "0.5-1 mile in grass",
        },
    },

    # =========================================================================
    # 18. DUFUR, OR — Wheat Belt / Gorge Transition
    # =========================================================================
    "dufur_or": {
        "center": [45.4571, -121.1292],
        "terrain_notes": (
            "Dufur (pop ~600) is a small wheat-belt town south of The Dalles on the "
            "dry side of the Cascades. Surrounded by continuous grass and wheat fields "
            "that create fast-moving fire potential. Elevation 1,300 ft on rolling terrain."
        ),
        "key_features": [
            {"name": "Tygh Ridge", "bearing": "W", "type": "ridge",
             "notes": "Elevation break between Gorge and interior; wind acceleration"},
        ],
        "elevation_range_ft": [1200, 2000],
        "wui_exposure": "moderate",
        "historical_fires": [
            {"name": "Dufur area grass fires", "year": 2018, "acres": 3000,
             "details": "Recurring large grass fires in surrounding wheat and rangeland."},
        ],
        "evacuation_routes": [
            {"route": "US-197 North/South", "direction": "N-S", "lanes": 2,
             "bottleneck": "Two-lane highway through grass/wheat", "risk": "Grass fire risk"},
        ],
        "fire_spread_characteristics": {
            "primary_wind_regime": "Gorge-influenced NW winds; dry continental air mass",
            "critical_corridors": ["US-197 grass corridor", "Tygh Ridge wind acceleration"],
            "rate_of_spread_potential": "Very high in wheat stubble; 200-400 chains/hr",
            "spotting_distance": "0.5-1 mile",
        },
    },

    # =========================================================================
    # 19. REDMOND, OR — High Desert Airport Town
    # =========================================================================
    "redmond_or": {
        "center": [44.2726, -121.1739],
        "terrain_notes": (
            "Redmond (pop ~35K) sits on the high desert east of the Cascades at 3,077 ft. "
            "Surrounded by juniper woodland and sagebrush steppe. Less WUI exposure than "
            "Bend but juniper fires can spread rapidly in wind events. Roberts Field airport "
            "serves as fire tanker base for Central Oregon."
        ),
        "key_features": [
            {"name": "Juniper Butte", "bearing": "E", "type": "butte",
             "notes": "Volcanic butte; juniper fuel surrounds city on east and north"},
            {"name": "Deschutes River Canyon (Cline Falls)", "bearing": "W", "type": "river_canyon",
             "notes": "Deep canyon between Redmond and Bend; fire barrier/corridor"},
        ],
        "elevation_range_ft": [2900, 3400],
        "wui_exposure": "moderate",
        "historical_fires": [
            {"name": "Juniper Hills fires", "year": 2020, "acres": 500,
             "details": "East wind-driven juniper fire near city limits."},
        ],
        "evacuation_routes": [
            {"route": "US-97 North/South", "direction": "N-S", "lanes": 4,
             "bottleneck": "Primary corridor shared with Bend", "risk": "Juniper fire can approach highway"},
            {"route": "US-126 East", "direction": "E", "lanes": 2,
             "bottleneck": "Two-lane through juniper", "risk": "Open terrain east of city"},
        ],
        "fire_spread_characteristics": {
            "primary_wind_regime": "SW thermal winds in summer; east winds in fall",
            "critical_corridors": ["US-97 juniper belt", "US-126 east corridor"],
            "rate_of_spread_potential": "Moderate to high in juniper; 50-100 chains/hr",
            "spotting_distance": "0.25-0.5 mile",
        },
    },

    # =========================================================================
    # 20. MCKENZIE BRIDGE, OR — Deep Canyon Community
    # =========================================================================
    "mckenzie_bridge_or": {
        "center": [44.1826, -122.1260],
        "terrain_notes": (
            "McKenzie Bridge is a tiny community (pop ~200) deep in the McKenzie River "
            "canyon surrounded by Willamette National Forest. The Holiday Farm Fire (2020) "
            "started near McKenzie Bridge and ran 30+ miles down-canyon in a single night "
            "during east winds. One of Oregon's most fire-vulnerable communities with "
            "essentially one road in/out (OR-126)."
        ),
        "key_features": [
            {"name": "McKenzie River Canyon", "bearing": "E-W", "type": "river_canyon",
             "notes": "Narrow canyon acts as wind tunnel during east wind events"},
            {"name": "Clear Lake (headwaters)", "bearing": "E", "type": "lake",
             "notes": "Ancient lava flow dammed river; old-growth forest surrounding"},
        ],
        "elevation_range_ft": [1400, 2200],
        "wui_exposure": "extreme",
        "historical_fires": [
            {"name": "Holiday Farm Fire", "year": 2020, "acres": 173393,
             "details": "Started near McKenzie Bridge during Labor Day east winds. Ran 30+ miles "
                        "down canyon overnight, destroying Blue River and Vida. One of most destructive "
                        "Oregon fires in modern history. 431 homes destroyed."},
        ],
        "evacuation_routes": [
            {"route": "OR-126 West (toward Eugene)", "direction": "W", "lanes": 2,
             "bottleneck": "Single road through canyon; fire blocked this during Holiday Farm",
             "risk": "EXTREME — canyon fire can trap residents; no alternative route"},
            {"route": "OR-126 East (toward Sisters)", "direction": "E", "lanes": 2,
             "bottleneck": "Mountain pass road; seasonal closures",
             "risk": "High — through continuous national forest"},
        ],
        "fire_spread_characteristics": {
            "primary_wind_regime": "Canyon-channeled east winds during offshore events; 40-60 mph",
            "critical_corridors": ["McKenzie River canyon (the Holiday Farm path)"],
            "rate_of_spread_potential": "Extreme; Holiday Farm covered 30+ miles in 12 hours",
            "spotting_distance": "1-3 miles in east wind canyon events",
        },
    },

    # =========================================================================
    # 21. VIDA, OR — McKenzie River Community (2020 Destroyed)
    # =========================================================================
    "vida_or": {
        "center": [44.1196, -122.5136],
        "terrain_notes": (
            "Vida is a small community along the McKenzie River west of Blue River. "
            "Largely destroyed by the Holiday Farm Fire in September 2020. Rebuilding "
            "is underway but the community remains extremely vulnerable to canyon fires "
            "driven by east winds. Dense Douglas-fir and western hemlock forest."
        ),
        "key_features": [
            {"name": "McKenzie River", "bearing": "E-W", "type": "river",
             "notes": "River corridor provides some firebreak but canyon walls channel wind"},
        ],
        "elevation_range_ft": [700, 1200],
        "wui_exposure": "extreme",
        "historical_fires": [
            {"name": "Holiday Farm Fire", "year": 2020, "acres": 173393,
             "details": "Vida largely destroyed; fire arrived from upcanyon during east wind event."},
        ],
        "evacuation_routes": [
            {"route": "OR-126 West (toward Springfield)", "direction": "W", "lanes": 2,
             "bottleneck": "Canyon road; only escape route west",
             "risk": "Canyon fire can cut this road, trapping residents"},
        ],
        "fire_spread_characteristics": {
            "primary_wind_regime": "East wind canyon events",
            "critical_corridors": ["McKenzie River canyon"],
            "rate_of_spread_potential": "Extreme during east wind events",
            "spotting_distance": "1-2 miles in canyon",
        },
    },

    # =========================================================================
    # 22. GRANTS PASS, OR — Rogue Valley Gateway
    # =========================================================================
    "grants_pass_or": {
        "center": [42.4390, -123.3284],
        "terrain_notes": (
            "Grants Pass (pop ~40K) is located in the Rogue Valley at the confluence "
            "of the Rogue River and the Illinois River drainage. Surrounded by Coast "
            "Range foothills with mixed oak-conifer forest. Hot, dry summers with "
            "triple-digit temperatures. Less directly threatened than Medford by the "
            "Almeda corridor but faces its own WUI challenges from the Applegate Valley "
            "and Coast Range to the west."
        ),
        "key_features": [
            {"name": "Rogue River", "bearing": "W through city", "type": "river",
             "notes": "River corridor provides partial firebreak but also recreation fire risk"},
            {"name": "Applegate Valley", "bearing": "SW", "type": "valley",
             "notes": "Wine country with oak woodland fuels; fire approach from SW"},
        ],
        "elevation_range_ft": [900, 1800],
        "wui_exposure": "high",
        "historical_fires": [
            {"name": "Chetco Bar Fire", "year": 2017, "acres": 191125,
             "details": "Massive fire to the SW; smoke impacts significant. Kalmiopsis Wilderness."},
        ],
        "evacuation_routes": [
            {"route": "I-5 North (to Roseburg)", "direction": "N", "lanes": 4,
             "bottleneck": "Canyon narrows between Grants Pass and Wolf Creek",
             "risk": "I-5 canyon section vulnerable to hillside fires"},
            {"route": "I-5 South (to Medford)", "direction": "S", "lanes": 4,
             "bottleneck": "Rogue River canyon section", "risk": "Primary corridor to Medford"},
            {"route": "US-199 South (Redwood Hwy)", "direction": "SW", "lanes": 2,
             "bottleneck": "Narrow mountain highway through heavy forest",
             "risk": "Illinois Valley fires can close this route"},
        ],
        "fire_spread_characteristics": {
            "primary_wind_regime": "Thermal low draws NW winds through Rogue Valley; hot and dry",
            "critical_corridors": ["Applegate Valley approach", "I-5 canyon to north"],
            "rate_of_spread_potential": "High in grass/oak; 100-200 chains/hr",
            "spotting_distance": "0.5-1 mile",
        },
    },

    # =========================================================================
    # 23. JACKSONVILLE, OR — Historic Gold Rush Town in Oak Woodland
    # =========================================================================
    "jacksonville_or": {
        "center": [42.3134, -122.9668],
        "terrain_notes": (
            "Jacksonville (pop ~3,000) is a historic gold rush town west of Medford "
            "surrounded by oak woodland and mixed conifer forest in the Applegate "
            "Valley foothills. Many historic wooden structures. WUI interface on "
            "all sides except east."
        ),
        "key_features": [
            {"name": "Applegate Valley", "bearing": "SW", "type": "valley",
             "notes": "Fire approach corridor from SW through oak and grass"},
        ],
        "elevation_range_ft": [1500, 2500],
        "wui_exposure": "high",
        "historical_fires": [],
        "evacuation_routes": [
            {"route": "OR-238 East (to Medford)", "direction": "E", "lanes": 2,
             "bottleneck": "Two-lane; primary escape to Medford", "risk": "Grass fire on valley floor"},
        ],
        "fire_spread_characteristics": {
            "primary_wind_regime": "Thermal draws from Applegate Valley",
            "critical_corridors": ["Applegate foothills approach"],
            "rate_of_spread_potential": "High in grass/oak; 100-150 chains/hr",
            "spotting_distance": "0.5 mile",
        },
    },

    # =========================================================================
    # 24. LAKEVIEW, OR — Remote High Desert
    # =========================================================================
    "lakeview_or": {
        "center": [42.1888, -120.3455],
        "terrain_notes": (
            "Lakeview (pop ~2,300) is the most remote and isolated city in Oregon, "
            "seat of Lake County. Sits at 4,800 ft on the high desert east of the "
            "Cascades. Surrounded by sagebrush steppe and juniper woodland. Extremely "
            "low humidity in summer with frequent dry lightning storms. Limited fire "
            "suppression resources."
        ),
        "key_features": [
            {"name": "Warner Mountains", "bearing": "E", "type": "mountain",
             "notes": "Juniper and ponderosa forest; lightning-caused fires common"},
            {"name": "Abert Rim", "bearing": "N", "type": "escarpment",
             "notes": "2,000-ft fault scarp; largest exposed fault in North America"},
        ],
        "elevation_range_ft": [4700, 6000],
        "wui_exposure": "moderate",
        "historical_fires": [
            {"name": "Barry Point Fire", "year": 2014, "acres": 55000,
             "details": "Large rangeland fire in Lake County; threatened Lakeview area ranches."},
        ],
        "evacuation_routes": [
            {"route": "US-395 North", "direction": "N", "lanes": 2,
             "bottleneck": "200 miles to next significant city (Bend via Burns)",
             "risk": "Extremely remote; help is hours away"},
            {"route": "US-395 South (to NV)", "direction": "S", "lanes": 2,
             "bottleneck": "Remote desert highway", "risk": "Limited services"},
        ],
        "fire_spread_characteristics": {
            "primary_wind_regime": "Afternoon thermals; dry thunderstorm downbursts",
            "critical_corridors": ["Warner Mountain front", "Goose Lake basin"],
            "rate_of_spread_potential": "High in sagebrush/grass; 100-300 chains/hr",
            "spotting_distance": "0.5-1 mile in sagebrush",
        },
    },

    # =========================================================================
    # 25. CHILOQUIN, OR — Klamath Basin / Sprague River
    # =========================================================================
    "chiloquin_or": {
        "center": [42.5779, -121.8667],
        "terrain_notes": (
            "Chiloquin (pop ~700) sits at the confluence of the Williamson and Sprague "
            "Rivers north of Klamath Falls. Klamath Tribes headquarters. The Bootleg "
            "Fire (2021, 413K acres) burned to the north and east. Mixed ponderosa "
            "pine and juniper with grass understory."
        ),
        "key_features": [
            {"name": "Sprague River Valley", "bearing": "E", "type": "river_valley",
             "notes": "Bootleg Fire area; lightning-prone terrain"},
        ],
        "elevation_range_ft": [4200, 5000],
        "wui_exposure": "high",
        "historical_fires": [
            {"name": "Bootleg Fire", "year": 2021, "acres": 413765,
             "details": "Largest US fire of 2021; burned within miles of Chiloquin. Generated pyrocumulonimbus."},
        ],
        "evacuation_routes": [
            {"route": "US-97 North/South", "direction": "N-S", "lanes": 2,
             "bottleneck": "Two-lane highway through timber/grass",
             "risk": "Fire can close highway to Klamath Falls and north"},
        ],
        "fire_spread_characteristics": {
            "primary_wind_regime": "Afternoon thermals; dry lightning common",
            "critical_corridors": ["Sprague River valley to Bootleg area"],
            "rate_of_spread_potential": "High; Bootleg Fire grew 40K+ acres per day at peak",
            "spotting_distance": "1-2 miles; Bootleg generated 40K+ ft pyrocu",
        },
    },

    # =========================================================================
    # 26. BONANZA, OR — High Desert Grassland
    # =========================================================================
    "bonanza_or": {
        "center": [42.1962, -121.4077],
        "terrain_notes": (
            "Bonanza (pop ~400) is a small ranching community east of Klamath Falls "
            "in the Langell Valley. Surrounded by grass and sagebrush with scattered "
            "juniper. Continental climate with extreme temperature swings and very low "
            "summer humidity."
        ),
        "key_features": [
            {"name": "Langell Valley", "bearing": "surrounding", "type": "valley",
             "notes": "Grass and sage rangeland; fast-moving fire terrain"},
        ],
        "elevation_range_ft": [4100, 4800],
        "wui_exposure": "moderate",
        "historical_fires": [],
        "evacuation_routes": [
            {"route": "OR-70 West (to Klamath Falls)", "direction": "W", "lanes": 2,
             "bottleneck": "Two-lane through grass/sage", "risk": "Grass fire can close road"},
        ],
        "fire_spread_characteristics": {
            "primary_wind_regime": "Afternoon thermals; occasional strong NW winds",
            "critical_corridors": ["Langell Valley grassland"],
            "rate_of_spread_potential": "Very high in grass; 200-400 chains/hr",
            "spotting_distance": "0.5 mile",
        },
    },

    # =========================================================================
    # 27. BLY, OR — Bootleg Fire Gateway
    # =========================================================================
    "bly_or": {
        "center": [42.3971, -120.9977],
        "terrain_notes": (
            "Bly (pop ~300) is a tiny community in the Sprague River valley, directly "
            "in the Bootleg Fire zone. The 2021 fire started nearby. Surrounded by "
            "ponderosa pine, juniper, and grass. Extremely remote with limited resources."
        ),
        "key_features": [
            {"name": "Sycan Marsh", "bearing": "N", "type": "marsh",
             "notes": "Large wetland that provides seasonal fire barrier"},
        ],
        "elevation_range_ft": [4300, 5200],
        "wui_exposure": "high",
        "historical_fires": [
            {"name": "Bootleg Fire", "year": 2021, "acres": 413765,
             "details": "Fire started near Bly; Level 3 evacuations for entire community."},
        ],
        "evacuation_routes": [
            {"route": "OR-140 West", "direction": "W", "lanes": 2,
             "bottleneck": "Remote two-lane highway", "risk": "Single route to Klamath Falls"},
        ],
        "fire_spread_characteristics": {
            "primary_wind_regime": "Dry lightning; afternoon thermals in mountain terrain",
            "critical_corridors": ["Sprague River valley (Bootleg corridor)"],
            "rate_of_spread_potential": "Extreme; Bootleg conditions",
            "spotting_distance": "1-3 miles with pyrocu development",
        },
    },

    # =========================================================================
    # 28. PAISLEY, OR — Summer Lake / Chewaucan Valley
    # =========================================================================
    "paisley_or": {
        "center": [42.6912, -120.5427],
        "terrain_notes": (
            "Paisley (pop ~250) sits in the Chewaucan River valley near Summer Lake "
            "in the high desert of Lake County. Surrounded by sagebrush, grass, and "
            "juniper. Winter Ridge to the west rises 3,000+ ft. Extremely remote."
        ),
        "key_features": [
            {"name": "Winter Ridge", "bearing": "W", "type": "escarpment",
             "notes": "3,000 ft escarpment creating wind acceleration over valley"},
            {"name": "Summer Lake", "bearing": "N", "type": "playa",
             "notes": "Alkali playa; natural firebreak when dry"},
        ],
        "elevation_range_ft": [4300, 5000],
        "wui_exposure": "moderate",
        "historical_fires": [],
        "evacuation_routes": [
            {"route": "OR-31 North/South", "direction": "N-S", "lanes": 2,
             "bottleneck": "Remote highway; 70 miles to Lakeview, 90 to La Pine",
             "risk": "Extreme remoteness; help hours away"},
        ],
        "fire_spread_characteristics": {
            "primary_wind_regime": "Downslope from Winter Ridge; dry lightning",
            "critical_corridors": ["Chewaucan Valley grass corridor"],
            "rate_of_spread_potential": "Very high in grass/sage",
            "spotting_distance": "0.5 mile",
        },
    },

    # =========================================================================
    # 29. PENDLETON, OR — Columbia Plateau / Blue Mountains Gateway
    # =========================================================================
    "pendleton_or": {
        "center": [45.6721, -118.7886],
        "terrain_notes": (
            "Pendleton (pop ~17K) sits in the Umatilla River valley at the northern "
            "edge of the Blue Mountains. Wheat and rangeland surround the city. "
            "Summer temperatures regularly exceed 100F. The Blue Mountains to the "
            "south have extensive timber susceptible to lightning fires."
        ),
        "key_features": [
            {"name": "Blue Mountains (south)", "bearing": "S", "type": "mountain_range",
             "notes": "Timber and mixed forest; lightning fire risk"},
            {"name": "Umatilla River Valley", "bearing": "E-W", "type": "river_valley",
             "notes": "Wheat and grass; fast fire spread potential"},
        ],
        "elevation_range_ft": [1000, 2500],
        "wui_exposure": "moderate",
        "historical_fires": [
            {"name": "Range fires", "year": 2020, "acres": 10000,
             "details": "Multiple large rangeland fires during 2020 east wind event."},
        ],
        "evacuation_routes": [
            {"route": "I-84 East/West", "direction": "E-W", "lanes": 4,
             "bottleneck": "Blue Mountain passes to east (Cabbage Hill)",
             "risk": "Grass fire can approach highway corridors"},
            {"route": "US-395 South", "direction": "S", "lanes": 2,
             "bottleneck": "Climbs into Blue Mountains", "risk": "Forest fire risk"},
        ],
        "fire_spread_characteristics": {
            "primary_wind_regime": "NW winds through Columbia Basin; Blue Mt thermals",
            "critical_corridors": ["Umatilla Valley grass corridor", "Blue Mountain front"],
            "rate_of_spread_potential": "Very high in grass/wheat; 200+ chains/hr",
            "spotting_distance": "0.5-1 mile in grass",
        },
    },

    # =========================================================================
    # 30. LA GRANDE, OR — Grande Ronde Valley
    # =========================================================================
    "la_grande_or": {
        "center": [45.3246, -118.0878],
        "terrain_notes": (
            "La Grande (pop ~13K) sits in the Grande Ronde Valley surrounded by Blue "
            "Mountains on all sides. Valley floor at 2,788 ft. Mt. Emily (6,000+ ft) "
            "looms to the north with dense timber. Continental climate with hot, dry "
            "summers. University town (Eastern Oregon University)."
        ),
        "key_features": [
            {"name": "Mt. Emily", "bearing": "N", "type": "mountain",
             "notes": "6,000 ft; dense timber above city; fire approach from north"},
            {"name": "Grande Ronde River", "bearing": "through valley", "type": "river",
             "notes": "Valley floor agriculture transitioning to forest on slopes"},
        ],
        "elevation_range_ft": [2700, 4000],
        "wui_exposure": "high",
        "historical_fires": [
            {"name": "Elbow Creek Fire", "year": 2007, "acres": 48000,
             "details": "Major Blue Mountain fire that threatened La Grande area communities."},
        ],
        "evacuation_routes": [
            {"route": "I-84 West (Cabbage Hill)", "direction": "W", "lanes": 4,
             "bottleneck": "Steep mountain grades; Blue Mountain pass",
             "risk": "Forest fire on pass can close I-84"},
            {"route": "I-84 East (toward Baker City)", "direction": "E", "lanes": 4,
             "bottleneck": "Ladd Canyon section", "risk": "Canyon fire approach"},
            {"route": "OR-82 East (to Wallowa)", "direction": "E", "lanes": 2,
             "bottleneck": "Mountain highway; remote", "risk": "Forest fire risk"},
        ],
        "fire_spread_characteristics": {
            "primary_wind_regime": "Valley thermal circulation; afternoon NW winds",
            "critical_corridors": ["Mt. Emily front", "Grande Ronde River valley"],
            "rate_of_spread_potential": "High in grass/timber interface; 50-100 chains/hr",
            "spotting_distance": "0.5-1 mile from timber",
        },
    },

    # =========================================================================
    # 31. BAKER CITY, OR — Elkhorn Mountains
    # =========================================================================
    "baker_city_or": {
        "center": [44.7749, -117.8344],
        "terrain_notes": (
            "Baker City (pop ~10K) sits in the Baker Valley at 3,450 ft between the "
            "Elkhorn Mountains (9,000+ ft) to the west and the Wallowa-Whitman NF. "
            "Historic gold mining town. Surrounded by grass, sage, and juniper with "
            "conifer forest on mountain slopes. Continental climate."
        ),
        "key_features": [
            {"name": "Elkhorn Mountains", "bearing": "W", "type": "mountain_range",
             "notes": "9,000+ ft peaks with dense timber; fire risk from west"},
        ],
        "elevation_range_ft": [3400, 5000],
        "wui_exposure": "moderate",
        "historical_fires": [],
        "evacuation_routes": [
            {"route": "I-84 South/North", "direction": "N-S", "lanes": 4,
             "bottleneck": "Mountain passes both directions", "risk": "Canyon and forest fire risk"},
        ],
        "fire_spread_characteristics": {
            "primary_wind_regime": "Mountain valley winds; dry lightning common",
            "critical_corridors": ["Elkhorn Mountain front", "Baker Valley grassland"],
            "rate_of_spread_potential": "Moderate to high; grass and sage",
            "spotting_distance": "0.5 mile",
        },
    },

    # =========================================================================
    # 32. ENTERPRISE, OR — Wallowa County Seat
    # =========================================================================
    "enterprise_or": {
        "center": [45.4268, -117.2788],
        "terrain_notes": (
            "Enterprise (pop ~2,000) is the county seat of Wallowa County, gateway to "
            "the Wallowa Mountains and Eagle Cap Wilderness. Sits at 3,757 ft in a "
            "valley with ponderosa pine and mixed conifer approaching from all sides. "
            "One of Oregon's most remote towns."
        ),
        "key_features": [
            {"name": "Wallowa Mountains", "bearing": "S", "type": "mountain_range",
             "notes": "Steepest mountains in Oregon; backcountry lightning fires"},
        ],
        "elevation_range_ft": [3700, 5000],
        "wui_exposure": "high",
        "historical_fires": [],
        "evacuation_routes": [
            {"route": "OR-82 West (to La Grande)", "direction": "W", "lanes": 2,
             "bottleneck": "Minam Canyon; narrow mountain road",
             "risk": "Only highway to outside world; forest fire closes it"},
            {"route": "OR-3 North (to Lewiston, ID)", "direction": "N", "lanes": 2,
             "bottleneck": "Remote mountain highway", "risk": "Limited alternative"},
        ],
        "fire_spread_characteristics": {
            "primary_wind_regime": "Mountain valley winds; dry lightning frequent",
            "critical_corridors": ["Wallowa Mountain front", "Minam Canyon"],
            "rate_of_spread_potential": "Moderate in mixed forest; high in grass",
            "spotting_distance": "0.5-1 mile",
        },
    },

    # =========================================================================
    # 33. JOSEPH, OR — Wallowa Lake Gateway
    # =========================================================================
    "joseph_or": {
        "center": [45.3543, -117.2296],
        "terrain_notes": (
            "Joseph (pop ~1,100) is at the foot of Wallowa Lake and the Wallowa "
            "Mountains. Tourist destination with art galleries and mountain recreation. "
            "Dead-end road — the highway ends at Wallowa Lake. Dense forest surrounds "
            "the community on three sides."
        ),
        "key_features": [
            {"name": "Wallowa Lake", "bearing": "S", "type": "lake",
             "notes": "Glacial lake; dead-end road beyond it"},
        ],
        "elevation_range_ft": [4100, 5000],
        "wui_exposure": "high",
        "historical_fires": [],
        "evacuation_routes": [
            {"route": "OR-82 North (to Enterprise)", "direction": "N", "lanes": 2,
             "bottleneck": "Only route out; 6 miles to Enterprise",
             "risk": "Dead-end community; fire between Joseph and Enterprise traps residents"},
        ],
        "fire_spread_characteristics": {
            "primary_wind_regime": "Mountain drainage winds; dry lightning",
            "critical_corridors": ["Wallowa Lake corridor (dead-end)"],
            "rate_of_spread_potential": "Moderate in mixed forest",
            "spotting_distance": "0.5 mile",
        },
    },

    # =========================================================================
    # 34. JOHN DAY, OR — Central Blue Mountains
    # =========================================================================
    "john_day_or": {
        "center": [44.4160, -118.9530],
        "terrain_notes": (
            "John Day (pop ~1,700) sits in the John Day River valley surrounded by "
            "Blue Mountain foothills. Juniper and ponderosa at lower elevations, mixed "
            "conifer above. Remote — 4+ hours from any major city. Limited fire "
            "suppression resources."
        ),
        "key_features": [
            {"name": "Strawberry Mountain (9,038 ft)", "bearing": "S", "type": "peak",
             "notes": "Highest point in Blue Mountains; wilderness area with fire risk"},
        ],
        "elevation_range_ft": [3000, 4500],
        "wui_exposure": "moderate",
        "historical_fires": [
            {"name": "Canyon Creek Complex", "year": 2015, "acres": 110000,
             "details": "Massive fire in Blue Mountains near John Day; largest Oregon fire of 2015."},
        ],
        "evacuation_routes": [
            {"route": "US-26 East/West", "direction": "E-W", "lanes": 2,
             "bottleneck": "Mountain highway; remote", "risk": "Fire can close in either direction"},
            {"route": "US-395 North/South", "direction": "N-S", "lanes": 2,
             "bottleneck": "Remote highway", "risk": "Limited alternative routes"},
        ],
        "fire_spread_characteristics": {
            "primary_wind_regime": "Mountain valley thermals; dry lightning frequent",
            "critical_corridors": ["John Day River valley", "Canyon Creek corridor"],
            "rate_of_spread_potential": "High; Canyon Creek Complex grew rapidly",
            "spotting_distance": "0.5-1 mile in timber",
        },
    },

    # =========================================================================
    # 35. SWEET HOME, OR — South Santiam Canyon Mouth
    # =========================================================================
    "sweet_home_or": {
        "center": [44.3968, -122.7351],
        "terrain_notes": (
            "Sweet Home (pop ~10K) sits at the mouth of the South Santiam canyon where "
            "it opens into the Willamette Valley. During east wind events, the canyon "
            "accelerates winds from the Cascades into town. Forest surrounds the city "
            "on the east and south. Green Peter and Foster reservoirs upstream."
        ),
        "key_features": [
            {"name": "South Santiam Canyon", "bearing": "E", "type": "river_canyon",
             "notes": "Wind acceleration corridor during east events; fire pathway into town"},
            {"name": "Green Peter Reservoir", "bearing": "E", "type": "reservoir",
             "notes": "Canyon narrows above reservoir; limited road access"},
        ],
        "elevation_range_ft": [500, 1500],
        "wui_exposure": "high",
        "historical_fires": [
            {"name": "Lionshead Fire", "year": 2020, "acres": 204000,
             "details": "Major Cascade fire during Labor Day east winds; smoke and evacuation impact."},
        ],
        "evacuation_routes": [
            {"route": "US-20 West (to Albany)", "direction": "W", "lanes": 2,
             "bottleneck": "Two-lane highway to Willamette Valley", "risk": "Primary escape route"},
            {"route": "US-20 East (toward Santiam Pass)", "direction": "E", "lanes": 2,
             "bottleneck": "Canyon road through continuous forest", "risk": "Forest fire risk"},
        ],
        "fire_spread_characteristics": {
            "primary_wind_regime": "East wind acceleration through Santiam canyon; foehn-type warming",
            "critical_corridors": ["South Santiam canyon mouth"],
            "rate_of_spread_potential": "High during east wind events",
            "spotting_distance": "0.5-1 mile",
        },
    },

    # =========================================================================
    # 36. ROSEBURG, OR — Umpqua Valley
    # =========================================================================
    "roseburg_or": {
        "center": [43.2165, -123.3417],
        "terrain_notes": (
            "Roseburg (pop ~24K) sits in the Umpqua Valley, one of Oregon's drier "
            "west-side valleys. Surrounded by mixed oak-conifer forest on surrounding "
            "hills. Hotter and drier than the Willamette Valley due to terrain sheltering. "
            "I-5 corridor city with timber industry heritage."
        ),
        "key_features": [
            {"name": "South Umpqua River", "bearing": "through city", "type": "river",
             "notes": "River valley floor; residential along floodplain"},
            {"name": "Cow Creek Canyon", "bearing": "S", "type": "canyon",
             "notes": "Canyon corridor connecting to Rogue Valley; hot air transport"},
        ],
        "elevation_range_ft": [400, 1500],
        "wui_exposure": "moderate",
        "historical_fires": [
            {"name": "Douglas Complex", "year": 2013, "acres": 48000,
             "details": "Multiple fires near Roseburg during lightning event."},
        ],
        "evacuation_routes": [
            {"route": "I-5 North (to Eugene)", "direction": "N", "lanes": 4,
             "bottleneck": "Hills section north of Roseburg", "risk": "Fire can approach I-5"},
            {"route": "I-5 South (to Grants Pass)", "direction": "S", "lanes": 4,
             "bottleneck": "Canyon Creek pass section", "risk": "Canyon fire risk"},
        ],
        "fire_spread_characteristics": {
            "primary_wind_regime": "Thermal draws from Rogue Valley through Cow Creek; NW valley winds",
            "critical_corridors": ["Cow Creek canyon", "I-5 corridor"],
            "rate_of_spread_potential": "Moderate to high in grass/oak",
            "spotting_distance": "0.5 mile",
        },
    },

    # =========================================================================
    # 37. FLORENCE, OR — Coast / Siuslaw River
    # =========================================================================
    "florence_or": {
        "center": [43.9826, -124.0998],
        "terrain_notes": (
            "Florence (pop ~9K) sits at the mouth of the Siuslaw River on the Oregon "
            "coast. Normally moderated by marine layer, but during east wind events the "
            "marine layer retreats and hot, dry air from the interior flows over the "
            "Coast Range. Shore pine and coastal forest fuels. The Tillamook Burns "
            "(1930s-50s) demonstrate that Oregon coast forests can burn catastrophically."
        ),
        "key_features": [
            {"name": "Siuslaw River", "bearing": "E", "type": "river",
             "notes": "Corridor from interior through Coast Range to ocean"},
            {"name": "Oregon Dunes", "bearing": "S", "type": "dunes",
             "notes": "Sand dunes provide natural firebreak south of town"},
        ],
        "elevation_range_ft": [0, 500],
        "wui_exposure": "low",
        "historical_fires": [],
        "evacuation_routes": [
            {"route": "US-101 North/South", "direction": "N-S", "lanes": 2,
             "bottleneck": "Coastal highway; bridges over rivers", "risk": "Limited capacity"},
            {"route": "OR-126 East (to Eugene)", "direction": "E", "lanes": 2,
             "bottleneck": "Coast Range highway through forest", "risk": "Forest fire during east wind"},
        ],
        "fire_spread_characteristics": {
            "primary_wind_regime": "Normally marine; east wind events bring dry interior air",
            "critical_corridors": ["Siuslaw River corridor (east wind path)"],
            "rate_of_spread_potential": "Low normally; extreme during east wind events in slash/timber",
            "spotting_distance": "0.5-1 mile in east wind events",
        },
    },

    # =========================================================================
    # 38. COTTAGE GROVE, OR — South Willamette / Coast Range Interface
    # =========================================================================
    "cottage_grove_or": {
        "center": [43.7976, -123.0595],
        "terrain_notes": (
            "Cottage Grove (pop ~11K) sits at the south end of the Willamette Valley "
            "where it narrows into the Coast Range foothills. Row River corridor to "
            "the east. Timber industry town with mixed conifer forest surrounding on "
            "three sides. I-5 corridor."
        ),
        "key_features": [
            {"name": "Row River", "bearing": "E", "type": "river",
             "notes": "Canyon corridor into Cascade foothills; timber land"},
        ],
        "elevation_range_ft": [600, 1500],
        "wui_exposure": "moderate",
        "historical_fires": [],
        "evacuation_routes": [
            {"route": "I-5 North (to Eugene)", "direction": "N", "lanes": 4,
             "bottleneck": "20 miles to Eugene", "risk": "Good capacity"},
            {"route": "I-5 South (to Roseburg)", "direction": "S", "lanes": 4,
             "bottleneck": "Mountain pass section", "risk": "Forest fire risk on pass"},
        ],
        "fire_spread_characteristics": {
            "primary_wind_regime": "Valley winds; east wind events affect canyon corridors",
            "critical_corridors": ["Row River canyon", "I-5 corridor"],
            "rate_of_spread_potential": "Moderate in timber/grass interface",
            "spotting_distance": "0.25-0.5 mile",
        },
    },

    # =========================================================================
    # 39. DRAIN, OR — Umpqua Valley North
    # =========================================================================
    "drain_or": {
        "center": [43.6590, -123.3184],
        "terrain_notes": (
            "Drain (pop ~1,200) is a small community in the Umpqua Valley between "
            "Cottage Grove and Roseburg. Coast Range foothills with timber and grass. "
            "I-5 corridor."
        ),
        "key_features": [],
        "elevation_range_ft": [300, 1000],
        "wui_exposure": "low",
        "historical_fires": [],
        "evacuation_routes": [
            {"route": "I-5 North/South", "direction": "N-S", "lanes": 4,
             "bottleneck": "Good access", "risk": "Low"},
        ],
        "fire_spread_characteristics": {
            "primary_wind_regime": "Valley winds",
            "critical_corridors": ["I-5 corridor margins"],
            "rate_of_spread_potential": "Moderate in grass/brush",
            "spotting_distance": "0.25 mile",
        },
    },

    # =========================================================================
    # 40. MYRTLE CREEK, OR — Southern Umpqua Valley
    # =========================================================================
    "myrtle_creek_or": {
        "center": [42.9957, -123.2917],
        "terrain_notes": (
            "Myrtle Creek (pop ~3,500) sits in the South Umpqua Valley between "
            "Roseburg and Canyonville. Surrounded by oak woodland and mixed conifer "
            "on surrounding hills. Hotter than Roseburg. Fire risk from grass and "
            "oak during summer."
        ),
        "key_features": [
            {"name": "South Umpqua River", "bearing": "through town", "type": "river",
             "notes": "Valley floor corridor"},
        ],
        "elevation_range_ft": [600, 1500],
        "wui_exposure": "moderate",
        "historical_fires": [],
        "evacuation_routes": [
            {"route": "I-5 North/South", "direction": "N-S", "lanes": 4,
             "bottleneck": "Canyon narrows south of town", "risk": "Canyon fire risk"},
        ],
        "fire_spread_characteristics": {
            "primary_wind_regime": "Valley thermals; Cow Creek draws hot air from south",
            "critical_corridors": ["South Umpqua corridor", "I-5 canyon"],
            "rate_of_spread_potential": "Moderate to high in grass/oak",
            "spotting_distance": "0.5 mile",
        },
    },

    # =========================================================================
    # 41. GRASS VALLEY, OR — Sherman County Wheat Belt
    # =========================================================================
    "grass_valley_or": {
        "center": [45.3054, -120.7534],
        "terrain_notes": (
            "Grass Valley (pop ~160) is a tiny wheat-belt community in Sherman County. "
            "Surrounded by continuous dryland wheat and grass. No forest. Fires here "
            "are wind-driven grass fires that spread at extreme rates. Very remote."
        ),
        "key_features": [],
        "elevation_range_ft": [2000, 2800],
        "wui_exposure": "low",
        "historical_fires": [],
        "evacuation_routes": [
            {"route": "OR-97 North/South", "direction": "N-S", "lanes": 2,
             "bottleneck": "Two-lane through wheat", "risk": "Grass fire can cross road"},
        ],
        "fire_spread_characteristics": {
            "primary_wind_regime": "Strong W-NW winds; Columbia Basin influence",
            "critical_corridors": ["Open wheat/grassland — fire can approach from any direction"],
            "rate_of_spread_potential": "Extreme in wheat stubble; 400+ chains/hr",
            "spotting_distance": "0.5-1 mile",
        },
    },

    # =========================================================================
    # 42. CANYON CITY, OR — John Day Gold Belt
    # =========================================================================
    "canyon_city_or": {
        "center": [44.3907, -118.9498],
        "terrain_notes": (
            "Canyon City (pop ~700) is adjacent to John Day in the Blue Mountains. "
            "Historic gold mining town at the mouth of Canyon Creek. Dense timber on "
            "surrounding slopes. The Canyon Creek Complex (2015) burned 110,000 acres "
            "nearby."
        ),
        "key_features": [
            {"name": "Canyon Creek", "bearing": "S", "type": "drainage",
             "notes": "Fire corridor into Blue Mountain timber"},
        ],
        "elevation_range_ft": [3100, 4500],
        "wui_exposure": "moderate",
        "historical_fires": [
            {"name": "Canyon Creek Complex", "year": 2015, "acres": 110000,
             "details": "Largest Oregon fire of 2015; burned in Blue Mountains near Canyon City."},
        ],
        "evacuation_routes": [
            {"route": "US-395 North/South", "direction": "N-S", "lanes": 2,
             "bottleneck": "Remote highway", "risk": "Fire can close in either direction"},
        ],
        "fire_spread_characteristics": {
            "primary_wind_regime": "Canyon thermals; dry lightning",
            "critical_corridors": ["Canyon Creek drainage"],
            "rate_of_spread_potential": "High in mixed fuel",
            "spotting_distance": "0.5-1 mile",
        },
    },

    # =========================================================================
    # 43. PRAIRIE CITY, OR — Southern Blue Mountains
    # =========================================================================
    "prairie_city_or": {
        "center": [44.4571, -118.7124],
        "terrain_notes": (
            "Prairie City (pop ~900) is east of John Day in the Blue Mountains. "
            "Near Strawberry Mountain Wilderness. Surrounded by ponderosa pine and "
            "mixed conifer at mountain valley interface."
        ),
        "key_features": [
            {"name": "Strawberry Mountain", "bearing": "S", "type": "peak",
             "notes": "9,038 ft; wilderness with lightning fire risk"},
        ],
        "elevation_range_ft": [3500, 5000],
        "wui_exposure": "moderate",
        "historical_fires": [],
        "evacuation_routes": [
            {"route": "US-26 West (to John Day)", "direction": "W", "lanes": 2,
             "bottleneck": "Mountain highway", "risk": "Forest fire risk"},
        ],
        "fire_spread_characteristics": {
            "primary_wind_regime": "Mountain thermals; dry lightning frequent",
            "critical_corridors": ["Strawberry Mountain front"],
            "rate_of_spread_potential": "Moderate in mixed forest",
            "spotting_distance": "0.5 mile",
        },
    },

    # =========================================================================
    # WASHINGTON (12 cities)
    # =========================================================================

    # =========================================================================
    # 1. CHELAN, WA — Lakeside town, 2015 Chelan Complex
    # =========================================================================
    "chelan_wa": {
        "center": [47.8407, -120.0160],
        "terrain_notes": (
            "Chelan sits at the southeastern tip of Lake Chelan, a 50.5-mile-long glacially "
            "carved fjord-like lake that is the third-deepest lake in the United States (1,486 ft). "
            "The city occupies a narrow bench between the lakeshore (elev ~1,100 ft) and steep, "
            "south-facing hillsides of Chelan Butte (elev ~3,892 ft) that rise abruptly 2,800 ft "
            "above town. These south- and west-facing slopes are covered in dry cheatgrass, "
            "sagebrush, and scattered ponderosa pine — classic flashy fuels that carry fire rapidly "
            "uphill. The Chelan River gorge to the east channels winds between the Columbia River "
            "corridor and the lake basin. The combination of steep terrain, solar-heated south "
            "aspects, and wind acceleration through the lake-valley convergence zone creates "
            "extreme fire behavior conditions. During the 2015 Chelan Complex, five fires ignited "
            "simultaneously around the south end of the lake and merged into a wind-driven "
            "firestorm that overran the town, destroying 82 structures including the Chelan Lumber "
            "Company and multiple residences within the urban growth boundary. The town's WUI "
            "boundary extends directly into high-hazard fuels on Chelan Butte. Tourism population "
            "in summer can triple the year-round population, with thousands of visitors in "
            "lakeside resorts, RV parks, and vacation rentals — many unfamiliar with evacuation "
            "routes. The orchard economy (apples, cherries) also brings seasonal agricultural "
            "workers housed in temporary structures."
        ),
        "key_features": [
            {"name": "Lake Chelan", "bearing": "NW", "type": "water/terrain", "notes": "50.5-mi glacial lake, 1,486 ft deep; provides water supply but lake-effect winds can accelerate fire spread along shoreline corridors"},
            {"name": "Chelan Butte", "bearing": "S", "type": "terrain", "notes": "3,892 ft prominence directly above town; south-facing slopes with flashy fuels, fire runs uphill toward summit then crowns over into town"},
            {"name": "Columbia River / US 97A corridor", "bearing": "SE", "type": "terrain/transport", "notes": "Major wind corridor; gap winds funnel between Chelan basin and Columbia Plateau"},
            {"name": "Chelan River Gorge", "bearing": "E", "type": "terrain", "notes": "Narrow gorge connecting Lake Chelan outlet to Columbia River; channels wind and creates venturi acceleration"},
            {"name": "Lakeside Park / Downtown", "bearing": "center", "type": "urban", "notes": "Dense commercial/tourist core at lakeshore; limited defensible space on south edge"},
        ],
        "elevation_range_ft": [1079, 3892],
        "wui_exposure": "extreme",
        "historical_fires": [
            {"name": "Chelan Complex", "year": 2015, "acres": 95000, "details": "Five fires merged on Aug 14; wind-driven firestorm destroyed 82 structures; 1,000+ evacuated; Chelan Lumber Company lost; $100M+ damages; fires burned into city limits"},
            {"name": "Chelan Butte Fire", "year": 2015, "acres": 500, "details": "Part of the complex; started on Chelan Butte's south face and raced uphill into structures on the ridge"},
            {"name": "Apple Acres Fire", "year": 2025, "acres": 2000, "details": "Forced Level 2 evacuations; closed Highway 97; demonstrated continued vulnerability of US 97 corridor"},
            {"name": "First Creek Fire", "year": 2015, "acres": 800, "details": "One of five fires in the Chelan Complex; burned near First Creek drainage west of town"},
        ],
        "evacuation_routes": [
            {"route": "US 97A south to Wenatchee", "direction": "S/SE", "lanes": 2, "bottleneck": "Single 2-lane highway along Columbia River; only 2,800-12,000 ADT capacity; closures during 2015 and 2025 fires", "risk": "Route passes through fire-prone terrain for 40 miles; multiple fires have closed this corridor"},
            {"route": "SR 150 west to Manson", "direction": "W", "lanes": 2, "bottleneck": "Dead-end route to Manson; no through-connection; evacuees must return to Chelan to exit", "risk": "Leads into another fire-vulnerable community with single-road access; closed during 2015 fires"},
            {"route": "US 97 north to Pateros", "direction": "N", "lanes": 2, "bottleneck": "Passes through steep canyon terrain along Columbia; historically closed by Carlton Complex fires", "risk": "Narrow canyon road vulnerable to rockfall and fire closure simultaneously"},
            {"route": "Lake Chelan boat evacuation", "direction": "NW", "lanes": 0, "bottleneck": "Lady of the Lake ferry has limited capacity; no nighttime service; dock congestion", "risk": "Weather-dependent; smoke reduces visibility; not viable for mass evacuation"},
        ],
        "fire_spread_characteristics": {
            "primary_wind_regime": "Diurnal lake-valley circulation with strong afternoon upslope/upvalley winds; synoptic events produce gap winds from Columbia Plateau funneling through Chelan River gorge at 25-40 mph; east wind events push fire westward into town from Chelan Butte",
            "critical_corridors": [
                "Chelan Butte south-facing slope — flashy fuels carry fire from US 97A corridor directly into south-side neighborhoods",
                "Chelan River gorge — wind acceleration zone connecting Columbia River to lake basin",
                "Lake Chelan south shore — fire can spread along steep shoreline slopes above lakeside resorts",
                "First Creek and vicinity — drainage channels funnel fire uphill into developed areas"
            ],
            "rate_of_spread_potential": "Extreme in grass/sage on Chelan Butte (3-5 mph with 20-ft flame lengths); moderate-high in mixed conifer on surrounding ridges; 2015 Complex demonstrated 10,000+ acre runs in single burning periods",
            "spotting_distance": "1-2 miles in grass/sage with 30+ mph winds; bark/ember transport from ponderosa pine can reach 0.5 mile; upslope terrain enhances lofting"
        },
        "infrastructure_vulnerabilities": {
            "water_system": "Chelan Water Department serves 9,355 connections from surface water; East Chelan Reservoir Project ($9M) addresses pressure issues; system stressed during simultaneous firefighting and domestic demand; gravity-fed from lake is reliable but distribution capacity limits concurrent fire suppression",
            "power": "Chelan County PUD hydroelectric (Lake Chelan Dam); above-ground distribution lines vulnerable to fire damage; 2015 fires caused widespread outages; limited backup generation for critical facilities",
            "communications": "Cell towers on Chelan Butte vulnerable to fire damage; 2015 fires degraded cell service during peak evacuation; limited landline redundancy in rural areas around lake",
            "medical": "Lake Chelan Community Hospital (25-bed critical access); nearest Level II trauma is Central Washington Hospital in Wenatchee (40 mi south on fire-vulnerable US 97A); medical helicopter operations limited by smoke"
        },
        "demographics_risk_factors": {
            "population": 4222,
            "seasonal_variation": "Summer tourism triples effective population to 12,000+; Labor Day and 4th of July peak periods coincide with peak fire season; vacation rental occupants unfamiliar with evacuation procedures",
            "elderly_percentage": "~22% over 65 (median age 46.7); significant retiree population in lakeside communities",
            "mobile_homes": "Several mobile home parks on south and east edges of town in high-exposure WUI zones; limited defensible space",
            "special_needs_facilities": "Heritage Heights assisted living; Lake Chelan Community Hospital long-term care; seasonal agricultural worker housing with limited fire notification systems"
        }
    },

    # =========================================================================
    # 9. CLE ELUM, WA — I-90 corridor, upper Kittitas Valley
    # =========================================================================
    "cle_elum_wa": {
        "center": [47.1954, -120.9383],
        "terrain_notes": (
            "Cle Elum (pop 2,078) sits at the western gateway of the Kittitas Valley where I-90 "
            "descends from Snoqualmie Pass into the upper Yakima River basin at 1,909 ft elevation. "
            "The city is flanked by dense conifer forest on three sides — the Cascade Range to the "
            "west, Teanaway drainage to the northeast, and Cle Elum Ridge to the south — creating "
            "a forested bowl with the town at its bottom. This is the transition zone between the "
            "wet western Cascades and the dry eastern slopes, producing a 'humidity cliff' where "
            "relative humidity can drop 30-40% in 10 miles during east wind events. Cle Elum is "
            "directly in the Snoqualmie Pass wind corridor, experiencing the same gap winds as "
            "Ellensburg (40-60+ mph) but with the added danger of dense forest fuels rather than "
            "grass. The 2012 Table Mountain Fire (near the Liberty/Swauk area north of town) "
            "forced evacuations and demonstrated vulnerability of the north approach. The 2017 "
            "Jolly Mountain Fire burned nearly 31,000 acres in the Teanaway drainage just "
            "northeast of town, forcing emergency evacuations and threatening the Cle Elum Lake "
            "watershed. Adjacent to Roslyn (1.5 miles west) and South Cle Elum, the combined "
            "communities share fire risk. The Suncadia Resort development west of town has pushed "
            "luxury WUI development into heavy forest. I-90 provides the primary evacuation "
            "corridor but can be overwhelmed by wind-driven fire crossing the interstate."
        ),
        "key_features": [
            {"name": "Snoqualmie Pass / I-90 corridor", "bearing": "W", "type": "transport/meteorological", "notes": "Primary evacuation route AND primary wind corridor; gap winds descend pass into town; fire can close I-90"},
            {"name": "Teanaway River drainage", "bearing": "NE", "type": "terrain", "notes": "Dense forest extending northeast; 2017 Jolly Mountain Fire burned 31,000 acres in this drainage; fire approach from NE through continuous conifer"},
            {"name": "Cle Elum Ridge / South side", "bearing": "S", "type": "terrain", "notes": "Forested ridge south of town; steep slopes; fire can run uphill and crown over into developed areas"},
            {"name": "Suncadia Resort / Roslyn interface", "bearing": "W", "type": "urban/WUI", "notes": "Luxury resort development pushed into heavy forest; Roslyn (100th percentile wildfire risk nationally) is 1.5 miles west; continuous forest connects both communities"},
            {"name": "Cle Elum Lake / dam", "bearing": "NW", "type": "water/infrastructure", "notes": "Bureau of Reclamation reservoir; watershed threatened by 2017 fire; dam infrastructure provides some firebreak but surrounding forest is dense"},
        ],
        "elevation_range_ft": [1900, 6500],
        "wui_exposure": "extreme",
        "historical_fires": [
            {"name": "Jolly Mountain Fire", "year": 2017, "acres": 31000, "details": "Lightning-caused Aug 11 in Teanaway; grew to 31,000 acres over 3+ months; emergency evacuations of Cle Elum area; threatened Cle Elum Lake watershed; 15% contained at peak; overwhelmed local suppression capacity"},
            {"name": "Table Mountain / Liberty fires", "year": 2012, "acres": 2500, "details": "Wildfires in Swauk/Table Mountain area N of town; Level 1-3 evacuations; Liberty and surrounding communities evacuated; national forest closures east of SR 97"},
            {"name": "Taylor Bridge Fire", "year": 2012, "acres": 23500, "details": "Ignited on SR 10 east of Cle Elum; gap winds drove fire east; 61 homes destroyed in Kittitas Valley; demonstrated how quickly fire moves through this corridor"},
        ],
        "evacuation_routes": [
            {"route": "I-90 east to Ellensburg", "direction": "E", "lanes": 4, "bottleneck": "Best capacity; 4-lane interstate; 25 miles to Ellensburg through open valley", "risk": "Grass fire can cross I-90 in wind events; Taylor Bridge Fire demonstrated fire spread across the corridor; wind-driven smoke reduces visibility to near-zero"},
            {"route": "I-90 west over Snoqualmie Pass to Seattle", "direction": "W", "lanes": 4, "bottleneck": "4-lane interstate but climbs 1,100 ft to pass summit through dense forest; pass closures for fire, wind, or winter weather", "risk": "Heading INTO wind corridor during gap-wind events; dense forest on pass; wildfire closure of I-90 over pass would be catastrophic for all east-side communities"},
            {"route": "SR 903 north to Cle Elum Lake", "direction": "N", "lanes": 2, "bottleneck": "Dead-end road to lake/campgrounds; no through-route; leads into forest fire zone", "risk": "TRAP: leads deeper into forest; Jolly Mountain Fire threatened this area; no exit beyond lake; campground visitors can be trapped"},
            {"route": "SR 10 / local roads south through South Cle Elum", "direction": "S", "lanes": 2, "bottleneck": "Local roads with limited capacity; converge back to I-90 or valley roads", "risk": "Fire from south approaches through Cle Elum Ridge; limited alternative to I-90"},
        ],
        "fire_spread_characteristics": {
            "primary_wind_regime": "Snoqualmie Pass gap winds (identical mechanism to Ellensburg but with forest fuels): marine push events create 40-60+ mph westerly winds descending pass; east wind (foehn) events bring hot, dry downslope winds from east; transition-zone humidity gradient means fuels dry rapidly during east wind events",
            "critical_corridors": [
                "I-90 / Snoqualmie Pass corridor — wind-aligned fire runway through dense forest; gap winds push fire east at extreme rates",
                "Teanaway River drainage — 2017 Jolly Mountain Fire demonstrated this corridor; fire approach from NE through continuous conifer",
                "Cle Elum Ridge — south-facing slopes with afternoon solar heating; fire runs uphill toward ridgetop then crowns over",
                "Roslyn-Cle Elum forest interface — continuous dense forest between communities; fire in this zone threatens both towns simultaneously"
            ],
            "rate_of_spread_potential": "Extreme in dense conifer: crown fire at 1-3 mph; gap-wind-driven fire in forest can exceed 3 mph; Jolly Mountain Fire grew 4,000 acres in a single day; transition-zone fuels (dry grass understory + conifer overstory) create ladder fuel conditions that facilitate rapid crown fire initiation",
            "spotting_distance": "1-3 miles from crown fire; gap winds can transport embers across I-90 (200+ ft); Jolly Mountain Fire demonstrated long-range spotting into Teanaway drainage; dense conifer produces abundant firebrand material"
        },
        "infrastructure_vulnerabilities": {
            "water_system": "City of Cle Elum water from wells and Cle Elum River; Bureau of Reclamation infrastructure (Cle Elum Dam) provides watershed storage; fire threatening watershed could contaminate supply; hillside homes may have pressure issues during fire",
            "power": "Kittitas County PUD and Puget Sound Energy; major transmission lines cross Snoqualmie Pass through fire-prone forest; gap-wind events damage above-ground distribution; power loss triggers loss of individual well pumps in rural areas",
            "communications": "Cell coverage limited in surrounding valleys; towers on ridges in fire-prone locations; I-90 corridor has coverage but side drainages (Teanaway, Cle Elum Lake) have gaps; emergency notification for recreationists in national forest is limited",
            "medical": "No hospital in Cle Elum; nearest is Kittitas Valley Healthcare in Ellensburg (25 mi east) or hospitals in west-side communities via I-90 (80+ mi); medical helicopter operations limited by smoke and wind; Suncadia Resort has first-aid but no emergency care"
        },
        "demographics_risk_factors": {
            "population": 2078,
            "seasonal_variation": "Suncadia Resort and outdoor recreation dramatically increase summer/weekend population; I-90 corridor travelers use Cle Elum as rest/fuel stop; Cle Elum Lake campgrounds add seasonal population; winter ski traffic at Snoqualmie Pass creates year-round visitor patterns",
            "elderly_percentage": "~20% over 65; retirement community development (Suncadia); historic town character attracts retirees",
            "mobile_homes": "Manufactured housing in Cle Elum and South Cle Elum; older units from logging/mining era; some in flood-prone and fire-prone locations",
            "special_needs_facilities": "No hospital; no assisted living in city; Suncadia Resort guests may include mobility-limited visitors; campground visitors with no local knowledge; South Cle Elum has separate jurisdiction complicating unified evacuation"
        }
    },

    # =========================================================================
    # 4. ELLENSBURG, WA — Kittitas Valley wind corridor
    # =========================================================================
    "ellensburg_wa": {
        "center": [46.9965, -120.5478],
        "terrain_notes": (
            "Ellensburg (pop 21,210) sits in the heart of the Kittitas Valley, a broad east-west "
            "trending valley between the Cascade Range to the west and the Manastash and Umtanum "
            "Ridges to the south. The valley is the outlet of the Snoqualmie Pass wind corridor, "
            "one of the most powerful gap-wind features in the Pacific Northwest. When pressure "
            "gradients develop across the Cascades, marine air funnels through Snoqualmie Pass "
            "(elev 3,022 ft) and accelerates as it descends 2,000+ ft into the Kittitas Valley, "
            "regularly producing sustained winds of 40-60 mph with gusts exceeding 80 mph at the "
            "pass and 50-60 mph in the valley. These winds are the defining fire risk factor for "
            "Ellensburg: the 2012 Taylor Bridge Fire demonstrated how a small ignition (welding "
            "sparks during bridge construction on SR 10) can explode into a 23,500-acre wind-"
            "driven fire that destroys 61 homes in conditions that overwhelm suppression efforts. "
            "The city is surrounded by a sea of dryland wheat stubble, CRP grassland, and "
            "sagebrush — flashy fuels that burn at highway speed in wind events. Central "
            "Washington University (10,000 students) is located in the city center. I-90 runs "
            "east-west through the valley, providing evacuation capacity but also serving as a "
            "fire corridor when grass fires cross the interstate. The Yakima River canyon to the "
            "south (SR 821) is another confined route vulnerable to closure."
        ),
        "key_features": [
            {"name": "Snoqualmie Pass wind corridor", "bearing": "W", "type": "meteorological", "notes": "Gap wind acceleration zone; sustained 40-60 mph winds during pressure gradient events; primary fire driver for entire Kittitas Valley"},
            {"name": "Manastash Ridge", "bearing": "S", "type": "terrain", "notes": "Ridge forming southern valley wall; sagebrush and grassland on north slopes; Manastash Creek drainage provides fire approach vector"},
            {"name": "Umtanum Ridge", "bearing": "SW", "type": "terrain", "notes": "Basalt ridge with grass/sage fuels; L.T. Murray Wildlife Area on slopes; fire can approach from Yakima Training Center"},
            {"name": "I-90 / SR 10 corridor", "bearing": "W-E", "type": "transport", "notes": "Interstate provides evacuation capacity but grass fires cross I-90 in wind events; SR 10 follows Yakima River and was site of Taylor Bridge Fire ignition"},
            {"name": "Central Washington University", "bearing": "center", "type": "institutional", "notes": "10,000 students and staff; campus in city center; evacuation of student body compounds traffic"},
        ],
        "elevation_range_ft": [1500, 3022],
        "wui_exposure": "high",
        "historical_fires": [
            {"name": "Taylor Bridge Fire", "year": 2012, "acres": 23500, "details": "Welding sparks on SR 10 bridge ignited grass during Red Flag Warning (Aug 13); winds 5-30 mph drove fire; 61 homes destroyed; 1,000 firefighters; $59.75M settlement; burned for 15 days"},
            {"name": "Vantage Highway fires", "year": 2018, "acres": 45000, "details": "Wind-driven grass fire east of Ellensburg; I-90 closures; demonstrated vast extent of flashy fuels surrounding city"},
            {"name": "Kittitas Valley grass fires", "year": 2024, "acres": 500, "details": "Wind-driven fire SW of Ellensburg quickly contained; gap winds accelerated spread; ongoing pattern of wind-driven grass fires"},
        ],
        "evacuation_routes": [
            {"route": "I-90 east to Moses Lake/Spokane", "direction": "E", "lanes": 4, "bottleneck": "Best capacity route but grass fires have crossed I-90 during wind events; visibility reduced by smoke", "risk": "Wide-open grassland on both sides; fire can cross divided highway in extreme wind; wildfire closures have occurred"},
            {"route": "I-90 west to Cle Elum/Seattle", "direction": "W", "lanes": 4, "bottleneck": "4-lane interstate but climbs into forested terrain toward Snoqualmie Pass; winter closures; wind events", "risk": "Heading into wind corridor during gap-wind events; Cle Elum area has own fire risk; pass can close"},
            {"route": "US 97 north to Wenatchee via Blewett Pass", "direction": "N", "lanes": 2, "bottleneck": "2-lane mountain road over 4,102-ft pass; slow with truck traffic; limited capacity", "risk": "Forested route through fire-prone terrain; pass closure creates long detour"},
            {"route": "SR 821 south through Yakima River Canyon", "direction": "S", "lanes": 2, "bottleneck": "Narrow canyon road; 23 miles of confined route with no alternate exits; scenic but deadly if fire enters canyon", "risk": "Basalt walls, grass/sage fuels on slopes, limited turnouts; fire in canyon would trap evacuees"},
        ],
        "fire_spread_characteristics": {
            "primary_wind_regime": "Snoqualmie Pass gap winds dominate: marine push events create pressure gradient that accelerates westerly flow to 40-60+ mph in valley; thermal low development over Columbia Basin enhances afternoon winds; nocturnal drainage winds from surrounding ridges",
            "critical_corridors": [
                "I-90 corridor from Cle Elum to Vantage — wind-aligned grass fire runway spanning 60+ miles",
                "Manastash Creek drainage — channels fire from forested ridges into south edge of city",
                "Yakima River canyon (SR 821) — confined fire spread corridor with no escape",
                "SR 10 / Taylor Creek area — proven ignition zone where fire reached city outskirts in 2012"
            ],
            "rate_of_spread_potential": "EXTREME in grass/sage: 5-10+ mph spread rates documented during gap-wind events; flame lengths 15-25 ft in sagebrush; Taylor Bridge Fire spread 10+ miles in first 12 hours; CRP grasslands provide continuous fine fuels across entire valley floor",
            "spotting_distance": "2-4 miles in grass with 50+ mph winds; firebrands from sage can travel 1+ mile; fires routinely cross I-90 (4 lanes + median) during wind events, indicating spotting distances exceed 200 ft even across firebreaks"
        },
        "infrastructure_vulnerabilities": {
            "water_system": "City of Ellensburg water from Yakima River and wells; adequate supply but hillside areas south and west of town have reduced pressure during high-demand events; CWU campus has independent fire suppression system",
            "power": "Kittitas County PUD and Puget Sound Energy; extensive above-ground transmission lines extremely vulnerable to wind damage (gap winds regularly down power lines, causing ignitions); wind farm infrastructure on ridges adds to grid complexity",
            "communications": "Cell towers on surrounding ridges vulnerable to wind damage and fire; gap-wind events can knock out communication infrastructure; CWU campus has independent systems; rural areas east and south have limited coverage",
            "medical": "Kittitas Valley Healthcare Hospital (25-bed critical access); nearest Level II trauma is Yakima (36 mi) or Wenatchee (65 mi); both routes traverse fire-vulnerable terrain; medical helicopter ops limited by wind events"
        },
        "demographics_risk_factors": {
            "population": 21210,
            "seasonal_variation": "CWU academic year adds ~10,000 students (Sept-June); Ellensburg Rodeo (Labor Day) brings 25,000+ visitors; irrigation season brings agricultural workers; summer recreation traffic on I-90",
            "elderly_percentage": "~12% over 65 (lower due to university; but surrounding rural areas have higher elderly populations)",
            "mobile_homes": "Significant manufactured housing stock on east and south edges of town; many older units; mobile home parks in wind-exposed locations",
            "special_needs_facilities": "Kittitas Valley Healthcare extended care; Hal Holmes Community Center (evacuation shelter); CWU dormitories with 3,000+ students requiring coordinated evacuation; multiple rural homesteads with elderly residents"
        }
    },

    # =========================================================================
    # 8. ENTIAT, WA — Entiat River valley, Mills Canyon Fire 2014
    # =========================================================================
    "entiat_wa": {
        "center": [47.6731, -120.2050],
        "terrain_notes": (
            "Entiat (pop 1,326) is a small city at the confluence of the Entiat and Columbia Rivers "
            "in Chelan County, situated between the eastern foothills of the Cascade Range, Lake "
            "Entiat (Columbia River impoundment), and the mouth of the Entiat River valley. The "
            "city sits at approximately 750 ft elevation on a narrow bench between the river and "
            "steep hillsides that rise sharply to the Entiat Mountains (4,000-6,000 ft) to the "
            "west and southwest. The Entiat River valley extends 50+ miles west into the Glacier "
            "Peak Wilderness, through progressively denser forest that provides continuous fuel "
            "from the wilderness boundary to the city. The valley has a documented history of "
            "catastrophic fire: the 1988 Dinkelmann Fire burned through Mills Canyon (3 miles up "
            "the Entiat Valley), and the area was replanted only to be burned again by the 2014 "
            "Mills Canyon Fire (22,571 acres). The combination of young replanted trees, "
            "flammable shrubs, and residual dead fuel from the 1988 fire created what fire "
            "managers described as 'a Molotov cocktail' of fuels. Highway 97A is the sole "
            "through-route along the Columbia River, and Entiat River Road provides the only "
            "access up the valley. The town's original commercial district was flooded by Rocky "
            "Reach Dam construction, and the rebuilt town has limited redundancy in its infrastructure."
        ),
        "key_features": [
            {"name": "Entiat River valley", "bearing": "W", "type": "terrain", "notes": "50+ mile fire corridor from Glacier Peak Wilderness to Columbia River; 1988 and 2014 fires demonstrate recurring fire runs down valley; dense forest transitions to grass/sage at town"},
            {"name": "Mills Canyon", "bearing": "W/SW", "type": "terrain", "notes": "3 miles up-valley; burned 1988 (Dinkelmann Fire) and 2014 (Mills Canyon Fire, 22,571 acres); reburn area with high fuel loading from dead replanted trees"},
            {"name": "Columbia River / Lake Entiat", "bearing": "E", "type": "water/terrain", "notes": "River provides some firebreak on east side but steep hillsides above lake carry fire; Rocky Reach Dam downstream"},
            {"name": "Entiat Mountains", "bearing": "W/SW", "type": "terrain", "notes": "Cascade foothills rising 4,000-6,000 ft; steep south-facing slopes with grass/sage at lower elevations transitioning to conifer"},
            {"name": "US 97A corridor", "bearing": "N-S", "type": "transport", "notes": "Sole through-highway along Columbia River; fire can close this route; passes through steep terrain between Wenatchee (18 mi south) and Chelan (25 mi north)"},
        ],
        "elevation_range_ft": [720, 6000],
        "wui_exposure": "high",
        "historical_fires": [
            {"name": "Mills Canyon Fire", "year": 2014, "acres": 22571, "details": "Started from structure fire west of Columbia River July 8; burned through grass, sagebrush, and scattered timber; forced evacuations of Entiat area; reburn of 1988 Dinkelmann Fire area created extreme fire behavior in accumulated fuels"},
            {"name": "Dinkelmann Fire", "year": 1988, "acres": 6000, "details": "Burned Mills Canyon area; Forest Service replanted; young trees grew into dense fuel load that fed 2014 reburn — demonstrating 25-year fire cycle"},
            {"name": "Duncan Fire", "year": 2009, "acres": 1600, "details": "Burned south of Entiat along Columbia; grass/sage fire driven by winds; threatened structures along US 97A"},
        ],
        "evacuation_routes": [
            {"route": "US 97A south to Wenatchee", "direction": "S", "lanes": 2, "bottleneck": "Primary route; 18 miles along Columbia River to Wenatchee; 2-lane highway with limited passing", "risk": "Route passes through fire-prone terrain along river; steep hillsides above road can carry fire across highway; smoke visibility issues"},
            {"route": "US 97A north to Chelan", "direction": "N", "lanes": 2, "bottleneck": "25 miles to Chelan; 2-lane highway; passes through similar terrain vulnerability", "risk": "Leads to another fire-vulnerable community; terrain similar to southbound route; both directions may be simultaneously threatened"},
            {"route": "Entiat River Road west (up-valley)", "direction": "W", "lanes": 2, "bottleneck": "DEAD END into national forest; narrow road; no through-route; becomes a trap", "risk": "Leads deeper into fire zone; Mills Canyon Fire originated from this direction; road passes through reburn area; absolutely not an evacuation route — it's a trap"},
        ],
        "fire_spread_characteristics": {
            "primary_wind_regime": "Entiat Valley creates a natural wind funnel connecting Cascade foothills to Columbia River corridor; afternoon upvalley winds bring fire toward town from forest interface; Columbia River gap winds from east during pressure gradient events; nocturnal downvalley drainage flows push fire toward Columbia and town",
            "critical_corridors": [
                "Entiat River valley — 50-mile fire corridor from wilderness to town; 1988 and 2014 fires burned down this valley",
                "Mills Canyon reburn area — accumulated fuels from two fire cycles create extreme fire behavior potential",
                "US 97A Columbia corridor — fire can approach from north or south along river; steep hillsides carry fire across highway",
                "Mad River drainage — parallel valley to the south; fire can cross ridges between drainages"
            ],
            "rate_of_spread_potential": "High to extreme: Mills Canyon Fire grew from ignition to 5,000 acres overnight; reburn fuels (dead young trees + shrubs + residual logs) create extreme fire behavior; grass/sage transition zone at valley mouth carries fire at 3-6 mph; upvalley wind events can push crown fire down-valley toward town",
            "spotting_distance": "1-2 miles in mixed fuels; bark and ember transport from ponderosa pine and Douglas fir; valley terrain channels embers toward Columbia corridor; reburn fuel structure creates intense convection columns that loft embers"
        },
        "infrastructure_vulnerabilities": {
            "water_system": "City of Entiat water system; town was rebuilt after dam construction flooded original district; system is modern but small-capacity; fire suppression demand during major incident can stress supply; rural properties up-valley on individual wells",
            "power": "Chelan County PUD; above-ground distribution lines through fire-prone terrain; 2014 fire caused outages; lines along Entiat River Road particularly vulnerable; limited backup generation",
            "communications": "Limited cell coverage especially up-valley; single cell tower serves town; fire can damage repeater sites; rural areas along Entiat River Road have poor coverage; emergency notification system dependent on cell connectivity",
            "medical": "No hospital in Entiat; nearest is Central Washington Hospital in Wenatchee (18 mi south); Cascade Medical Center in Leavenworth (25 mi west — requires mountain road); medical helicopter limited by smoke; new fire station built post-2014 for improved local response"
        },
        "demographics_risk_factors": {
            "population": 1326,
            "seasonal_variation": "Summer recreation (Entiat River fishing, camping) increases population; orchard season brings agricultural workers; Lake Entiat boating activity; 100% rural census designation",
            "elderly_percentage": "~18% over 65; small-town demographics; aging agricultural community",
            "mobile_homes": "Manufactured housing in town and along Entiat River Road; older units in fire-prone locations; limited defensible space on many properties",
            "special_needs_facilities": "No hospital; no assisted living; school facilities serve as community shelter; US Aluminum Castings workforce (largest employer) concentrated in single location; agricultural worker housing with limited fire notification"
        }
    },

    # =========================================================================
    # 3. LEAVENWORTH, WA — Tumwater Canyon bottleneck, Bavarian village
    # =========================================================================
    "leavenworth_wa": {
        "center": [47.5962, -120.6615],
        "terrain_notes": (
            "Leavenworth (pop 2,263) is a Bavarian-themed tourist village nestled in a narrow "
            "valley at the confluence of the Wenatchee River and Icicle Creek, flanked by steep, "
            "forested mountain slopes rising 4,000-6,000 ft above the valley floor. The town sits "
            "at 1,168 ft elevation at a critical geographic chokepoint: US Highway 2 — the only "
            "east-west highway between Stevens Pass and Blewett Pass (a 70-mile gap) — threads "
            "through Tumwater Canyon immediately west of town, a narrow, deeply forested gorge "
            "with vertical rock walls where the Wenatchee River has carved through bedrock. This "
            "canyon is the single most critical evacuation bottleneck in the central Cascades: "
            "when fire or debris closes US 2 through Tumwater Canyon, Leavenworth is effectively "
            "cut off from western Washington. The only alternative route is Chumstick Highway "
            "(SR 209) north to US 2 at Coles Corner — a narrow, winding rural road with bridge "
            "restrictions. The valley's steep, south-facing slopes above town are covered in "
            "dense mixed conifer (Douglas fir, ponderosa pine) with heavy dead fuel loads from "
            "decades of fire suppression and insect kill (mountain pine beetle). Fires run uphill "
            "at extreme rates on these slopes and crown easily in the dense canopy. Icicle Creek "
            "corridor to the south provides another fire approach vector through the Alpine Lakes "
            "Wilderness interface. Tourism drives the economy: the village hosts over 2 million "
            "visitors annually for Oktoberfest, Christmas Lighting Festival, and summer recreation, "
            "with peak weekend populations exceeding 30,000 — potentially catastrophic for "
            "evacuation on a 2-lane highway system."
        ),
        "key_features": [
            {"name": "Tumwater Canyon", "bearing": "W", "type": "terrain/transport", "notes": "Narrow rock-walled gorge carrying US 2 and Wenatchee River; 21-mile section from Coles Corner; fires have closed this corridor multiple times; single-point evacuation failure"},
            {"name": "Icicle Creek corridor", "bearing": "S", "type": "terrain", "notes": "Valley extending south into Alpine Lakes Wilderness; Icicle Road provides access to campgrounds and trailheads; fire approach vector from south through dense forest"},
            {"name": "Tumwater Mountain", "bearing": "W/NW", "type": "terrain", "notes": "Steep forested slopes above canyon; fire on these slopes can close US 2 and trap town"},
            {"name": "Wedge Mountain / Chumstick area", "bearing": "N/NE", "type": "terrain", "notes": "North valley slopes; Chumstick Highway runs through this area; alternative evacuation route through fire-prone pine forest"},
            {"name": "Bavarian Village downtown", "bearing": "center", "type": "urban", "notes": "Dense tourist commercial district with timber-frame construction; narrow streets; limited fire breaks; 2M+ annual visitors"},
        ],
        "elevation_range_ft": [1100, 7000],
        "wui_exposure": "extreme",
        "historical_fires": [
            {"name": "Tumwater Canyon fires (multiple)", "year": 2024, "acres": 200, "details": "Two sudden wildfires in Tumwater Canyon closed US 2; fires devoured timber in hot/breezy conditions; demonstrated canyon closure vulnerability"},
            {"name": "Icicle Creek Fire", "year": 2015, "acres": 500, "details": "Fire near Icicle Road prompted evacuations and closure of US 2 from Icicle Road junction to Coles Corner; 49-mile highway section affected"},
            {"name": "Rat Creek Fire", "year": 2018, "acres": 6800, "details": "Burned in Wenatchee River drainage upstream of town; closed Highway 2; threatened water supply watershed"},
            {"name": "Hatchery Creek Fire", "year": 2012, "acres": 6200, "details": "Started near Leavenworth National Fish Hatchery on Icicle Creek; rapid uphill spread in steep terrain; forced level 3 evacuations; hundreds of homes threatened"},
        ],
        "evacuation_routes": [
            {"route": "US 2 east to Wenatchee", "direction": "E", "lanes": 2, "bottleneck": "Best available route but passes through fire-prone pine/sage transition zone for 20 miles", "risk": "Heavy tourist traffic creates congestion; 2-lane with limited passing; smoke visibility issues"},
            {"route": "US 2 west through Tumwater Canyon to Stevens Pass", "direction": "W", "lanes": 2, "bottleneck": "CRITICAL: Narrow canyon, single 2-lane road, no shoulders, vertical rock walls; closed by fire multiple times (2015, 2018, 2024, 2025)", "risk": "When closed, eliminates access to western WA for 70+ miles of Cascade crest; no alternate highway"},
            {"route": "Chumstick Highway (SR 209) north to Coles Corner", "direction": "N", "lanes": 2, "bottleneck": "Narrow rural road with bridge restrictions; low-speed winding alignment; limited capacity", "risk": "Passes through fire-prone pine forest; convergence with US 2 at Coles Corner can create secondary bottleneck; not designed for mass evacuation"},
            {"route": "Icicle Road south", "direction": "S", "lanes": 2, "bottleneck": "Dead-end road into Alpine Lakes Wilderness; no through-route; leads to campgrounds with trapped visitors", "risk": "Becomes a trap during fire; no exit at end of road; fire approach from south traps recreationists"},
        ],
        "fire_spread_characteristics": {
            "primary_wind_regime": "Cascade gap winds accelerating through Stevens Pass corridor descend through Tumwater Canyon; diurnal upvalley winds from Wenatchee Valley reach 15-25 mph by afternoon; east wind (foehn-type) events produce hot, dry downslope winds exceeding 35 mph",
            "critical_corridors": [
                "Tumwater Canyon — fire in canyon closes the sole westward evacuation route; steep canyon walls create extreme updrafts",
                "Icicle Creek drainage — south approach through dense conifer; fire runs upcanyon on afternoon winds directly toward town",
                "Chumstick drainage — north approach through ponderosa/Douglas fir; threatens alternate evacuation route",
                "Wenatchee River corridor east — fire spread along river valley toward town on diurnal valley winds"
            ],
            "rate_of_spread_potential": "Extreme on steep forested slopes (crown fire at 1-3 mph with 100+ ft flame lengths); terrain-driven fire runs on 40-60% slopes can achieve rates of 3-5 mph; decades of fire suppression have created continuous canopy fuels with heavy dead ladder fuels",
            "spotting_distance": "1-3 miles from crown fire in dense conifer; Tumwater Canyon creates chimney-effect lofting that can transport embers extraordinary distances; cross-canyon spotting can trap firefighters and evacuees"
        },
        "infrastructure_vulnerabilities": {
            "water_system": "City water from Wenatchee River and wells; treatment plant at valley floor is defensible but distribution lines to hillside homes vulnerable; fire flow capacity limited in upper-elevation residential areas; drought years reduce river levels",
            "power": "Chelan County PUD; overhead transmission lines through Tumwater Canyon extremely vulnerable to fire and tree-fall; loss of transmission isolates town from regional grid; limited emergency generation for extended outages",
            "communications": "Mountain terrain limits cell coverage to valley floor; towers on surrounding ridges vulnerable to fire; Tumwater Canyon has dead zones; satellite communication limited by steep terrain; radio repeater sites on ridges in fire-prone areas",
            "medical": "Cascade Medical Center (small critical access hospital/clinic); nearest major hospital is Central Washington Hospital in Wenatchee, 22 miles east on fire-vulnerable US 2; medical helicopter operations severely limited by canyon terrain and smoke"
        },
        "demographics_risk_factors": {
            "population": 2263,
            "seasonal_variation": "EXTREME: 2M+ annual visitors; peak weekends (Oktoberfest, Christmas Lighting) bring 30,000+ visitors to 2,300-person town; summer weekends 10,000-15,000; campgrounds and vacation rentals add thousands unfamiliar with evacuation routes",
            "elderly_percentage": "~20% over 65; retirement community character; Bavarian Village condo complexes have senior-heavy populations",
            "mobile_homes": "Limited within city; some manufactured housing in Peshastin (3 mi east) and along Chumstick Highway; rural homesteads with limited defensible space",
            "special_needs_facilities": "Cascade Medical Center long-term care; Mountain Meadows senior campus; multiple campgrounds with families and disabled visitors; Leavenworth National Fish Hatchery staff housing in fire zone"
        }
    },

    # =========================================================================
    # 10. MANSON, WA — Lake Chelan north shore, single road access
    # =========================================================================
    "manson_wa": {
        "center": [47.8853, -120.1583],
        "terrain_notes": (
            "Manson (pop 1,523) is an unincorporated agricultural community on the north shore of "
            "Lake Chelan, approximately 7 miles northwest of the city of Chelan. The community is "
            "built on bench terraces between the lakeshore (elev ~1,100 ft) and steep, forested "
            "hillsides rising to 4,000-5,000 ft above. Manson is designated as an 'at-risk "
            "community of catastrophic wildfire' in its Community Wildfire Protection Plan, and "
            "its most critical vulnerability is ACCESS: there is essentially a single road (SR 150 / "
            "Manson Highway) providing the only way in or out, connecting to Chelan 7 miles "
            "southeast along the lakeshore. This single-road access means that a fire between "
            "Manson and Chelan would trap the entire community with no vehicular escape route. "
            "The surrounding terrain is covered in dry grass, sagebrush, and scattered ponderosa "
            "pine on south-facing slopes, transitioning to mixed conifer forest at higher elevations. "
            "The community economy is based on orchards (apples, cherries, grapes/wine) and tourism, "
            "with significant agricultural worker populations in seasonal housing. Wapato Point "
            "Resort and other lakeside developments add tourist population during summer. "
            "The hillsides above Manson received fire during the 2015 Chelan Complex season, and "
            "the community has experienced multiple evacuation scares."
        ),
        "key_features": [
            {"name": "SR 150 / Manson Highway (sole access road)", "bearing": "SE", "type": "transport", "notes": "CRITICAL: Only road connecting Manson to Chelan and the highway network; fire on this 7-mile corridor traps entire community; shut down during past fires"},
            {"name": "Lake Chelan north shore", "bearing": "S", "type": "water/terrain", "notes": "Lake provides potential boat evacuation but limited capacity; steep terrain above lakeshore carries fire; north-shore developments in WUI zone"},
            {"name": "Manson hillsides (north/west)", "bearing": "N/W", "type": "terrain", "notes": "Steep slopes with grass/sage transitioning to conifer; south/east-facing aspects maximize solar heating; fire runs uphill above town"},
            {"name": "Wapato Point Resort / waterfront developments", "bearing": "S/SE", "type": "urban", "notes": "Tourist resort complex on lake; adds summer population; evacuation dependent on SR 150"},
            {"name": "Orchard benchlands", "bearing": "W/NW", "type": "agricultural", "notes": "Apple and cherry orchards provide some fuel break but irrigated only during growing season; dormant orchard vegetation can burn; worker housing in orchard areas"},
        ],
        "elevation_range_ft": [1079, 5000],
        "wui_exposure": "extreme",
        "historical_fires": [
            {"name": "Chelan Complex (Manson threats)", "year": 2015, "acres": 95000, "details": "Complex of fires on south end of Lake Chelan; SR 150 between Chelan and Manson shut down; Manson threatened; community evacuations considered; smoke impacts severe"},
            {"name": "Pioneer Fire", "year": 2024, "acres": 1500, "details": "Fire on north shore of Lake Chelan prompted Level 3 (GO NOW) evacuation orders for areas north of Manson; SR 150 threatened; demonstrated single-road vulnerability"},
            {"name": "Manson grassland fires", "year": 2024, "acres": 7, "details": "Small 7-acre fire prompted immediate Level 3 evacuation due to proximity to structures and single evacuation route; shows how even small fires trigger emergency response in single-access community"},
        ],
        "evacuation_routes": [
            {"route": "SR 150 southeast to Chelan", "direction": "SE", "lanes": 2, "bottleneck": "THE ONLY VEHICULAR EXIT: 7-mile 2-lane road along lakeshore to Chelan; fire between Manson and Chelan traps entire community; has been closed during fires", "risk": "EXTREME: Single point of failure; road passes through fire-prone terrain; closure means NO vehicular evacuation possible; CWPP identifies this as the community's primary vulnerability"},
            {"route": "Lake Chelan boat evacuation", "direction": "S/SE", "lanes": 0, "bottleneck": "Limited marina capacity; no organized boat evacuation plan; weather/wave conditions variable; smoke reduces visibility", "risk": "Not a reliable mass evacuation option; dependent on boat availability; no nighttime capability; cannot evacuate mobility-limited residents by boat"},
        ],
        "fire_spread_characteristics": {
            "primary_wind_regime": "Lake-valley diurnal circulation: afternoon upslope winds drive fire toward ridgetops; lake breeze effects create variable wind at shoreline; synoptic events channel winds along lake axis (NW-SE); gap winds from Cascade passes reach Lake Chelan basin",
            "critical_corridors": [
                "SR 150 corridor — fire along this 7-mile route cuts off the ONLY evacuation route for the entire community",
                "North-shore hillsides — steep grass/sage slopes above lakeside developments; fire runs uphill above Manson toward ridgeline",
                "Roses Lake / Grade Creek area — fire approach from north/west through forested terrain above orchards",
                "Lake Chelan south shore fire interaction — fires on opposite shore (2015 Complex) can spot across narrow lake sections"
            ],
            "rate_of_spread_potential": "High to extreme: grass/sage on hillsides carries fire at 3-5 mph; even small fires (7-acre 2024 incident) prompt Level 3 evacuations due to single-road vulnerability; steepness of terrain above town accelerates uphill spread; transition to conifer at higher elevation enables crown fire",
            "spotting_distance": "0.5-1.5 miles in grass/sage with wind; cross-lake spotting possible in extreme events (lake narrows to <1 mile at points); upslope terrain enhances lofting"
        },
        "infrastructure_vulnerabilities": {
            "water_system": "Community water system from wells and lake intake; agricultural irrigation demand in summer competes with fire suppression; system designed for residential/agricultural use, not mass fire suppression; limited hydrant coverage in rural orchard areas",
            "power": "Chelan County PUD; above-ground distribution lines along SR 150 vulnerable to fire; power loss would affect well pumps and emergency communications; limited backup generation",
            "communications": "Cell coverage limited on north shore; single tower area; terrain blocks signals in valleys above Manson; emergency notification must reach agricultural workers (language barriers) and tourists; SR 150 closure isolates community from cell towers in Chelan",
            "medical": "No medical facility in Manson; dependent on Lake Chelan Community Hospital in Chelan (7 mi via fire-vulnerable SR 150); medical helicopter operations limited by terrain and smoke; ambulance service from Chelan; if SR 150 is closed, NO medical access"
        },
        "demographics_risk_factors": {
            "population": 1523,
            "seasonal_variation": "Summer tourism at Wapato Point Resort and lakeside rentals doubles population; orchard season brings agricultural workers (significant Spanish-speaking population); 4th of July / summer weekends peak; seasonal residents may not know evacuation procedures",
            "elderly_percentage": "~18% over 65; retirement community element; lakeside homes with elderly residents; limited mobility options during evacuation",
            "mobile_homes": "Agricultural worker housing includes manufactured homes and temporary structures; some orchard housing in fire-prone hillside areas; limited defensible space",
            "special_needs_facilities": "No medical facility; no assisted living; agricultural worker housing with language barriers; Wapato Point Resort guests unfamiliar with local conditions; boat-dependent waterfront properties may resist vehicular evacuation"
        }
    },

    # =========================================================================
    # 12. OMAK/OKANOGAN, WA — 2015 Okanogan Complex, most fire-prone area
    # =========================================================================
    "omak_okanogan_wa": {
        "center": [48.4118, -119.5268],
        "terrain_notes": (
            "Omak (pop 4,845) and Okanogan (pop 2,379) are twin cities on the Okanogan River in "
            "Okanogan County — the most fire-prone county in Washington State. Located at "
            "approximately 843 ft elevation in a broad river valley, the cities are the commercial "
            "and governmental hub of Okanogan County (the largest county in WA at 5,315 sq mi). "
            "The Okanogan River valley runs north-south with sagebrush-covered benches and "
            "terraces rising to pine-forested hills on both sides. The Colville Indian Reservation "
            "borders Omak to the east, with its vast open grasslands and timber. Omak Creek enters "
            "from the east, providing a fire corridor from the reservation lands. The 2015 "
            "Okanogan Complex — the largest fire event in WA history by acreage at 304,782 acres — "
            "was composed of five lightning-caused fires that burned across the landscape surrounding "
            "these communities, forcing evacuations and killing three firefighters on the Twisp "
            "River Fire component. The 2014 Carlton Complex also threatened the broader Okanogan "
            "area, burning to the hills around Brewster (20 mi south). The area experiences hot, "
            "dry summers with temperatures regularly exceeding 100F, single-digit humidity, and "
            "frequent dry lightning storms that ignite multiple fires simultaneously. Okanogan "
            "County had the 2014 AND 2015 record-setting fires, plus the Twisp River Fire "
            "fatalities — making it ground zero for Washington wildfire risk. The county's large "
            "area, sparse population, and limited firefighting resources mean fires can grow "
            "unchecked for hours before significant suppression response arrives."
        ),
        "key_features": [
            {"name": "Okanogan River valley", "bearing": "N-S", "type": "terrain", "notes": "Broad valley with river providing some firebreak; sagebrush benches and terraces on both sides; wind corridor; US 97 runs through valley"},
            {"name": "Colville Indian Reservation", "bearing": "E", "type": "terrain", "notes": "Vast open grasslands and timber east of Omak; Omak Creek provides fire corridor from reservation; limited fire suppression resources on reservation lands"},
            {"name": "Conconully / Salmon Creek drainage", "bearing": "NW", "type": "terrain", "notes": "Valley extending northwest to Conconully; 2015 Okanogan Complex fires originated near Conconully; forested terrain with limited road access"},
            {"name": "Omak Lake / eastern benchlands", "bearing": "E/SE", "type": "terrain", "notes": "Arid benchlands east of town; Omak Lake (tribal land); vast grass and sagebrush with scattered pine; fire can approach from east across open terrain"},
            {"name": "US 97 / downtown corridor", "bearing": "N-S", "type": "transport/urban", "notes": "Primary highway through both cities; commercial strip development; evacuation route and fire exposure simultaneously"},
        ],
        "elevation_range_ft": [780, 6774],
        "wui_exposure": "extreme",
        "historical_fires": [
            {"name": "Okanogan Complex", "year": 2015, "acres": 304782, "details": "5 lightning-caused fires (Twisp River, Lime Belt, Beaver Lake, Blue Lake, Tunk Block); largest fire event in WA history by acreage; forced evacuations of Conconully, Twisp, Winthrop; 3 firefighters killed (Twisp River Fire component); 1,250+ firefighters deployed"},
            {"name": "Carlton Complex (area impacts)", "year": 2014, "acres": 256108, "details": "Burned to hills around Brewster (20 mi south of Omak); threatened Malott on Okanogan River; fire approached from Methow Valley; demonstrated vulnerability of entire Okanogan River corridor"},
            {"name": "Tunk Block Fire (component)", "year": 2015, "acres": 55000, "details": "Component of Okanogan Complex that burned closest to Omak; threatened communities north and east of city; burned through tribal lands and private ranch lands"},
            {"name": "Cold Springs Fire", "year": 2020, "acres": 189388, "details": "Burned east of Omak on Colville Reservation; one of largest fires in state that year; killed child; demonstrated continued extreme fire risk from reservation grasslands approaching Omak from east"},
        ],
        "evacuation_routes": [
            {"route": "US 97 south to Brewster/Chelan/Wenatchee", "direction": "S", "lanes": 2, "bottleneck": "Primary route south; 2-lane highway along Okanogan River; passes through Malott, Brewster — both threatened by 2014 Carlton Complex", "risk": "Route through fire-prone river corridor; Carlton Complex burned to Brewster; 80+ miles to Wenatchee through fire-vulnerable terrain"},
            {"route": "US 97 north to Canadian border", "direction": "N", "lanes": 2, "bottleneck": "2-lane highway north through Oroville to Canadian border; passes through fire-prone terrain", "risk": "International border crossing complications; fire can close highway; Oroville area has experienced fires"},
            {"route": "SR 20 west to Methow Valley / North Cascades", "direction": "W", "lanes": 2, "bottleneck": "2-lane mountain road over Loup Loup Pass (4,020 ft); closed by fire during 2015 Okanogan Complex; seasonal closures on North Cascades Highway beyond Winthrop", "risk": "Route through heavily forested terrain; passes through Twisp/Winthrop fire zone; Loup Loup Pass fire closure documented; SR 20 beyond Winthrop closed Nov-April"},
            {"route": "SR 155 south to Coulee Dam / Grand Coulee", "direction": "S/SE", "lanes": 2, "bottleneck": "2-lane highway through Colville Reservation; passes through Nespelem; limited capacity", "risk": "Route through reservation grasslands — 2020 Cold Springs Fire burned 189,000 acres in this area; limited infrastructure along route"},
        ],
        "fire_spread_characteristics": {
            "primary_wind_regime": "Okanogan Valley north-south channeling of synoptic winds; thermal convection creates strong afternoon upvalley winds; dry lightning storms are primary ignition source (2014 and 2015 fires both lightning-caused); east winds from Columbia Plateau bring extreme heat and low humidity; foehn-type winds from Cascades occasional but devastating",
            "critical_corridors": [
                "Okanogan River valley (N-S) — wind corridor connecting communities; fire can travel valley length",
                "Omak Creek drainage (E) — corridor from Colville Reservation grasslands into east side of Omak; Cold Springs Fire approach vector",
                "Salmon Creek / Conconully drainage (NW) — forested corridor; 2015 Okanogan Complex origin area",
                "Tunk Creek / north benchlands — 2015 Tunk Block Fire corridor; fire approaches from north through grass/sage"
            ],
            "rate_of_spread_potential": "EXTREME across multiple fuel types: grass/sage at 5-10+ mph during wind events; timber at 2-4 mph with crown fire; Okanogan Complex demonstrated multiple simultaneous fire runs of 10,000+ acres in single burning periods; dry lightning ignites dozens of starts simultaneously, overwhelming initial attack; area can have 50+ new ignitions in a single storm",
            "spotting_distance": "2-5 miles documented during Okanogan Complex; convective columns from large fires create their own weather; embers cross ridges and valleys; simultaneous spotting in multiple drainages; fires can merge across 10+ mile gaps through spotting alone"
        },
        "infrastructure_vulnerabilities": {
            "water_system": "Omak city water from wells and Okanogan River; adequate for normal use but mass fire suppression in WUI strains capacity; rural areas on individual wells lose water with power failure; tribal lands have separate water systems with varying capacity; Okanogan city water system is separate and smaller",
            "power": "Okanogan County PUD; extensive above-ground distribution across the county's 5,315 sq mi; fires regularly destroy miles of lines; weeks-long outages in rural areas documented during 2014 and 2015 fires; limited backup generation; cost of hardening lines across largest county in WA is prohibitive",
            "communications": "Okanogan County Emergency Management system; cell coverage limited outside of Omak/Okanogan valley; vast county area means many residents unreachable by cell; tribal communication systems separate; repeater sites on mountaintops vulnerable to fire; 2015 fires caused communication failures across county",
            "medical": "Mid-Valley Hospital in Omak (25-bed critical access); the only hospital serving a 5,315 sq mi county; nearest additional hospital is Wenatchee (95 mi south) or Spokane (175 mi east); medical helicopter operations regularly impossible due to smoke; EMS response times exceed 30 minutes for rural calls; tribal health facilities at Nespelem supplement"
        },
        "demographics_risk_factors": {
            "population": 9224,  # Omak 4,845 + Okanogan 2,379 + surrounding areas
            "seasonal_variation": "Omak Stampede (rodeo, Aug) brings thousands; summer recreation on Okanogan River; hunting season (Oct-Nov) brings visitors to rural areas; Colville Reservation events; agricultural season (orchards, ranching) adds workers",
            "elderly_percentage": "~20% over 65; rural aging population; tribal elders on reservation; limited mobility options for rural elderly",
            "mobile_homes": "Significant manufactured housing stock throughout county; older units; many on tribal lands; limited defensible space; some in isolated locations with single-road access; highest percentage of manufactured homes in any WA county",
            "special_needs_facilities": "Mid-Valley Hospital (only hospital in county); tribal health center at Nespelem; limited assisted living; 14.4% of county residents below poverty level; tribal populations with unique emergency management needs; vast rural population (county avg 8 people/sq mi) difficult to notify and evacuate"
        }
    },

    # =========================================================================
    # 7. PATEROS, WA — Destroyed by Carlton Complex 2014
    # =========================================================================
    "pateros_wa": {
        "center": [48.0514, -119.9030],
        "terrain_notes": (
            "Pateros (pop 593) is the smallest and perhaps most fire-devastated town in Washington "
            "State, located at the confluence of the Methow and Columbia Rivers at approximately "
            "900 ft elevation. The town was literally rebuilt in the 1960s when Wells Dam construction "
            "flooded the original commercial district, and then devastated again when the 2014 "
            "Carlton Complex destroyed 111 homes in and around town — representing roughly one-"
            "third of all housing in the community. The fire arrived on July 17, 2014, when hot "
            "winds propelled a firestorm 25 miles south from the Winthrop/Carlton area down the "
            "Methow Valley corridor, reaching Pateros at approximately 8 PM. The entire town was "
            "successfully evacuated with no casualties. Pateros is situated in a bowl where the "
            "Methow River meets the Columbia, surrounded by steep, barren hillsides covered in "
            "cheatgrass and sagebrush — some of the flashiest fuels in the state. The terrain "
            "creates a natural funnel: fire racing down the Methow Valley accelerates as the "
            "valley narrows approaching the Columbia, and wind corridors from both rivers converge "
            "at the town site. The community was still rebuilding infrastructure 5+ years after "
            "the fire, with a new well to improve water pressure and ongoing recovery efforts "
            "coordinated by the Okanogan County Long Term Recovery Group. SR 153 is the sole "
            "route north into the Methow Valley; US 97 runs north-south along the Columbia."
        ),
        "key_features": [
            {"name": "Methow River / Columbia River confluence", "bearing": "center", "type": "terrain", "notes": "Two river corridors converge at town; wind from both valleys meets here; fire funnel effect from Methow Valley corridor"},
            {"name": "Methow Valley corridor (north)", "bearing": "N", "type": "terrain", "notes": "50-mile fire corridor through which the Carlton Complex firestorm traveled 25 miles in one burning period to reach Pateros"},
            {"name": "Columbia River / Lake Pateros (Wells Dam pool)", "bearing": "E", "type": "water/terrain", "notes": "Columbia River impoundment provides water but surrounding hillsides are steep and covered in flashy fuels; Wells Dam 8 mi downstream"},
            {"name": "Chiliwist Valley", "bearing": "W", "type": "terrain", "notes": "Side valley west of Pateros; Carlton Complex burned homes and ranches in this drainage; fire approach vector from west"},
            {"name": "Alta Lake area", "bearing": "SW", "type": "terrain", "notes": "Recreational area southwest of town; multiple homes destroyed in 2014 fire; dispersed rural residences in high-fire-risk terrain"},
        ],
        "elevation_range_ft": [780, 3500],
        "wui_exposure": "extreme",
        "historical_fires": [
            {"name": "Carlton Complex", "year": 2014, "acres": 256108, "details": "Firestorm reached Pateros July 17; destroyed 111 homes in and around town (~1/3 of housing stock); entire town evacuated successfully; fire arrived at 8 PM after 25-mile run; destroyed homes in Chiliwist Valley, Alta Lake, and within city limits; $98M total damage across complex"},
            {"name": "Okanogan Complex", "year": 2015, "acres": 304782, "details": "Threatened Pateros area again just one year after Carlton Complex; demonstrated that the rebuilt community faces the same fire exposure; evacuations ordered"},
        ],
        "evacuation_routes": [
            {"route": "US 97 south to Chelan/Wenatchee", "direction": "S", "lanes": 2, "bottleneck": "Primary evacuation route; 2-lane highway along Columbia River; passes through steep terrain for 30+ miles to Chelan", "risk": "Canyon road vulnerable to fire closure; Apple Acres Fire (2025) closed US 97 in this corridor; terrain amplifies fire spread along highway"},
            {"route": "US 97 north to Okanogan/Omak", "direction": "N", "lanes": 2, "bottleneck": "2-lane highway along Columbia/Okanogan Rivers; passes through fire-prone terrain", "risk": "Carlton Complex and Okanogan Complex fires threatened this route; leads to another fire-vulnerable area"},
            {"route": "SR 153 north into Methow Valley", "direction": "N", "lanes": 2, "bottleneck": "CLOSED during Carlton Complex; the fire was COMING FROM this direction; single 2-lane road up narrow Methow Valley", "risk": "EXTREME: During 2014 Carlton Complex, this road was the fire corridor itself; evacuating north meant driving INTO the firestorm; SR 153 and SR 20 were closed simultaneously"},
            {"route": "Wells Dam Road east", "direction": "E", "lanes": 2, "bottleneck": "Limited local road; crosses Wells Dam but restricted access; not a primary evacuation route", "risk": "Dam security restrictions may limit evacuation use; road not designed for mass traffic"},
        ],
        "fire_spread_characteristics": {
            "primary_wind_regime": "Methow Valley corridor funnels north winds directly into Pateros; Columbia River corridor provides east-west wind component; convergence of two wind corridors at town site creates accelerated and turbulent wind patterns; synoptic events produce 30-50 mph winds through valley",
            "critical_corridors": [
                "Methow Valley corridor — 50-mile fire runway from Winthrop/Carlton to Pateros; Carlton Complex firestorm traveled this route in hours",
                "Chiliwist Valley — western approach; fire burned homes in this side valley in 2014",
                "Columbia River corridor — wind channeling from east or south; steep barren hillsides above river carry fire rapidly",
                "Alta Lake drainage — southwestern approach through dispersed rural residences"
            ],
            "rate_of_spread_potential": "EXTREME: Carlton Complex documented 25-mile fire run in single burning period reaching Pateros; flashy cheatgrass/sage fuels on surrounding slopes carry fire at 5-10 mph; steep terrain above town creates uphill fire acceleration; rate of spread exceeded all predictive models in 2014",
            "spotting_distance": "2-5 miles during Carlton Complex; wind-driven embers crossed ridges and valleys; firebrands ignited spot fires well ahead of main fire front; entire town was threatened simultaneously from multiple directions"
        },
        "infrastructure_vulnerabilities": {
            "water_system": "SEVERELY IMPACTED by 2014 fire: water reservoirs and telemetry equipment damaged; new well constructed post-fire to improve water pressure; system rebuilt but remains small-community scale; simultaneous fire suppression demand can overwhelm capacity",
            "power": "Okanogan County PUD / Douglas County PUD; above-ground lines destroyed in 2014 fire; rebuilt but same exposure to future fires; town experienced weeks-long outage during Carlton Complex",
            "communications": "Cell service limited; 2014 fire destroyed communication infrastructure; rebuilt but single points of failure remain; rural areas around town have poor coverage; emergency notification dependent on cell/internet",
            "medical": "No medical facilities in Pateros; nearest hospital is Mid-Valley Hospital in Omak (30 mi north) or Three Rivers Hospital in Brewster (15 mi south); medical helicopter impossible during fire; 911 response times 15+ min"
        },
        "demographics_risk_factors": {
            "population": 593,
            "seasonal_variation": "Summer recreation increases population with Lake Pateros visitors and Methow Valley travelers; hydroplane races bring weekend visitors; agricultural season brings orchard workers",
            "elderly_percentage": "~20% over 65; small-town demographics with aging population; many residents who survived 2014 fire are aging in place",
            "mobile_homes": "Manufactured housing represents significant portion of rebuilt housing stock post-2014; some replacement homes are manufactured; limited defensible space on small lots",
            "special_needs_facilities": "No hospital or medical facility; no assisted living; elderly residents in rebuilt homes; community still dealing with fire-related PTSD and mental health impacts from 2014; Okanogan County Long Term Recovery Group continues to assist"
        }
    },

    # =========================================================================
    # 11. ROSLYN, WA — Former coal town surrounded by forest
    # =========================================================================
    "roslyn_wa": {
        "center": [47.2235, -120.9931],
        "terrain_notes": (
            "Roslyn (pop 984) is a former coal mining town at 2,247 ft elevation in the Cascade "
            "Mountains of Kittitas County, about 80 miles east of Seattle and 1.5 miles west of "
            "Cle Elum. Founded in 1886 when Northern Pacific Railway prospectors found coal veins, "
            "the town reached a peak population of 4,000 during its mining heyday and produced "
            "over 50 million tons of coal before the last mine closed in 1963. Today Roslyn is "
            "famous as the filming location for the TV show 'Northern Exposure' and for its "
            "historic downtown listed on the National Register. The town ranks in the 100th "
            "percentile of wildfire risk to homes in Washington State and the 99th percentile "
            "nationally, according to the U.S. Forest Service. Roslyn is COMPLETELY SURROUNDED "
            "by dense forest: the city acquired a 300-acre 'Urban Forest' in 2004, and thousands "
            "of additional acres of Okanogan-Wenatchee National Forest and private timberland "
            "encircle the community. The forest consists of dense stands of Douglas fir, ponderosa "
            "pine, and grand fir with heavy dead fuel loads from decades of fire suppression and "
            "insect mortality. Nearby Ronald (a small community 1 mile west) was destroyed by fire "
            "in 1928 — an event that nearly spread to Roslyn and was only stopped by 2,000 "
            "volunteers and a fortuitous wind shift. The community has become a national model "
            "for community-led wildfire management through controlled burns and fuel reduction in "
            "the Urban Forest, but the surrounding landscape remains a continuous forest fuel bed."
        ),
        "key_features": [
            {"name": "Roslyn Urban Forest (300 acres)", "bearing": "surrounding", "type": "terrain/fuel", "notes": "City-owned forest encircling town; active fuel reduction program (controlled burns, thinning); serves as buffer but also fire approach vector if treatments lapse"},
            {"name": "Okanogan-Wenatchee National Forest", "bearing": "W/N/S", "type": "terrain", "notes": "Dense conifer forest on all sides; heavy dead fuel loads from fire suppression and beetle kill; continuous fuel from wilderness to town"},
            {"name": "Ronald / western approach", "bearing": "W", "type": "urban", "notes": "Small community 1 mile west; destroyed by fire in 1928; fire nearly spread to Roslyn; corridor between Ronald and Roslyn remains forested"},
            {"name": "Suncadia Resort development", "bearing": "E/SE", "type": "urban/WUI", "notes": "Luxury resort between Roslyn and Cle Elum; pushed development into forest; connected by continuous forest fuel"},
            {"name": "Coal Creek drainage", "bearing": "N", "type": "terrain", "notes": "Historic mining area with legacy coal seam exposure; drainage provides fire approach from north through dense forest"},
        ],
        "elevation_range_ft": [2100, 5500],
        "wui_exposure": "extreme",
        "historical_fires": [
            {"name": "Ronald Fire", "year": 1928, "acres": 500, "details": "Fire devastated neighboring Ronald (1 mi west) on Aug 18, destroying 32 houses and businesses; spread into forest threatening Roslyn; 2,000 miners, railroaders, and citizens fought fire; wind abatement saved Roslyn"},
            {"name": "Jolly Mountain Fire (nearby)", "year": 2017, "acres": 31000, "details": "Burned in Teanaway drainage NE of Cle Elum; threatened broader area; demonstrated massive fire potential in forests surrounding Roslyn/Cle Elum; emergency evacuations"},
            {"name": "Taylor Bridge Fire (nearby)", "year": 2012, "acres": 23500, "details": "Burned east in Kittitas Valley; demonstrated wind-driven fire behavior in the Snoqualmie Pass corridor that includes Roslyn"},
        ],
        "evacuation_routes": [
            {"route": "SR 903 east to Cle Elum, then I-90", "direction": "E", "lanes": 2, "bottleneck": "1.5 miles to Cle Elum; then access I-90; route passes through Suncadia Resort development in forest", "risk": "Short but forested corridor between towns; fire in Suncadia/Roslyn forest interface blocks this primary route; converges at Cle Elum with all other evacuees"},
            {"route": "SR 903 west through Ronald", "direction": "W", "lanes": 2, "bottleneck": "Passes through Ronald; continues to dead end at Cle Elum Lake; NO THROUGH ROUTE", "risk": "TRAP: Road leads to Cle Elum Lake with no exit; forest surrounds entire route; Ronald burned in 1928 on this corridor; not a viable evacuation"},
            {"route": "Local roads south", "direction": "S", "lanes": 2, "bottleneck": "Limited local roads converge back to SR 903 and I-90 through Cle Elum; no independent southern exit", "risk": "All routes funnel through Cle Elum; forest surrounds all roads; no alternative to SR 903"},
        ],
        "fire_spread_characteristics": {
            "primary_wind_regime": "Snoqualmie Pass gap winds descend through Cle Elum area at 30-50+ mph; Roslyn's valley position creates sheltering from worst gap winds but also traps smoke and embers; nocturnal drainage winds from surrounding ridges; east wind (foehn) events bring hot, dry air that rapidly lowers fuel moisture in surrounding dense forest",
            "critical_corridors": [
                "Roslyn-Cle Elum forest corridor — continuous dense conifer between towns; fire here blocks the ONLY evacuation route",
                "Coal Creek drainage north — fire approach from national forest through dense fuel directly to town",
                "Ronald-Roslyn corridor — 1928 fire path; forest has regrown between communities",
                "Suncadia development interface — luxury WUI development in continuous forest connecting to both Roslyn and Cle Elum"
            ],
            "rate_of_spread_potential": "High to extreme in dense conifer: crown fire at 1-3 mph; heavy dead fuel loads from fire suppression create ladder fuels; Urban Forest fuel reduction has reduced immediate risk around town but surrounding untreated forest remains at extreme potential; gap-wind events can turn moderate fire into crown fire rapidly",
            "spotting_distance": "1-3 miles in dense conifer with gap winds; Douglas fir bark produces prolific firebrands; surrounding terrain creates funnel effects for ember transport; Roslyn's valley position may create ember catch basin during wind events"
        },
        "infrastructure_vulnerabilities": {
            "water_system": "City of Roslyn water from Coal Creek watershed; limited storage; fire threatening watershed could contaminate supply; historic mining-era infrastructure; hydrant coverage limited in older neighborhoods; simultaneous fire suppression and domestic demand stresses system",
            "power": "Kittitas County PUD / Puget Sound Energy; above-ground lines through dense forest extremely vulnerable; wind events regularly damage lines; power loss affects well pumps throughout area; limited backup generation; restored historic buildings often have outdated electrical",
            "communications": "Limited cell coverage in valley; terrain blocks signals; single tower serves area; radio repeaters on surrounding ridges in fire-prone locations; historic downtown lacks modern communication infrastructure; fire-related communication failures documented in surrounding area during 2017 Jolly Mountain Fire",
            "medical": "No medical facility in Roslyn; nearest hospital is Kittitas Valley Healthcare in Ellensburg (30 mi east); medical access requires transit through Cle Elum; forest fire blocking SR 903 eliminates medical access entirely; volunteer fire department; limited EMS"
        },
        "demographics_risk_factors": {
            "population": 984,
            "seasonal_variation": "Tourism increases summer population (Northern Exposure filming location, outdoor recreation, Suncadia Resort visitors); weekend/holiday peaks; winter has some ski-related tourism from nearby Snoqualmie Pass",
            "elderly_percentage": "~22% over 65; retirement/artist community character; historic homes with elderly residents; limited mobility in some neighborhoods",
            "mobile_homes": "Some manufactured housing from mining era; older units; limited defensible space in densely treed lots; many historic homes with wood siding and roofing in close proximity to forest",
            "special_needs_facilities": "No hospital; no assisted living; historic town character means narrow streets and older buildings; volunteer fire department with limited capacity for mass evacuation; combined Roslyn/Cle Elum/South Cle Elum evacuation would overwhelm single I-90 corridor"
        }
    },

    # =========================================================================
    # 6. TWISP, WA — 2015 Twisp River Fire (3 LODD)
    # =========================================================================
    "twisp_wa": {
        "center": [48.3635, -120.1223],
        "terrain_notes": (
            "Twisp (pop 992) sits at the confluence of the Twisp River and Methow River in the "
            "heart of the Methow Valley at 1,903 ft elevation. The town occupies a narrow bench "
            "where the Twisp River valley opens into the main Methow Valley — a geography that "
            "creates a wind funnel effect as winds channeling down the Twisp River drainage "
            "accelerate into the broader valley. This exact configuration contributed to the "
            "August 19, 2015 tragedy: the Twisp River Fire started when tree branches struck a "
            "powerline in the Twisp River corridor, and strong shifting winds drove walls of "
            "flames and smoke onto a team of USFS firefighters attempting initial attack. "
            "Firefighters Richard Wheeler, Andrew Zajac, and Tom Zbyszewski were killed when "
            "their engine crashed in zero-visibility smoke on a winding dirt road. A fourth "
            "firefighter, Daniel Lyon, survived with 60-65% third-degree burns after exiting "
            "the vehicle and running through flames. The fire grew to 11,922 acres and reached "
            "the outskirts of Twisp within hours. The town is flanked by steep, forested slopes "
            "rising 3,000-5,000 ft above the valley floor on both east and west sides. The "
            "Twisp River valley extends west into the Okanogan-Wenatchee National Forest with "
            "dense mixed conifer under heavy fuel loading from fire suppression. TwispWorks "
            "(former ranger station campus) serves as a community hub. The town has the character "
            "of an arts community with historic downtown, but its geographic position in a "
            "narrow valley convergence zone makes it one of the most fire-vulnerable towns in "
            "the state."
        ),
        "key_features": [
            {"name": "Twisp River valley", "bearing": "W", "type": "terrain", "notes": "Narrow valley extending west into national forest; wind funnel effect at valley mouth; site of 2015 fatal fire; dense conifer with heavy fuel loading"},
            {"name": "Methow River main valley", "bearing": "N-S", "type": "terrain", "notes": "Main valley axis; fire corridor connecting Winthrop (7 mi N) to Pateros (30 mi S); Carlton Complex fire path"},
            {"name": "Twisp Butte / eastern slopes", "bearing": "E", "type": "terrain", "notes": "Steep slopes rising above town; south/west-facing aspects with dry grass and scattered pine; fire can race uphill and crown over into town"},
            {"name": "Balky Hill / western slopes", "bearing": "W", "type": "terrain", "notes": "Forested slopes above town; fire approach from Twisp River drainage drops into town; 2015 fire reached these slopes"},
            {"name": "TwispWorks campus / downtown", "bearing": "center", "type": "urban", "notes": "Former USFS ranger station converted to community campus; historic downtown with wood-frame structures; limited fire breaks"},
        ],
        "elevation_range_ft": [1750, 6500],
        "wui_exposure": "extreme",
        "historical_fires": [
            {"name": "Twisp River Fire", "year": 2015, "acres": 11922, "details": "LODD: Richard Wheeler, Andrew Zajac, Tom Zbyszewski killed Aug 19; started from powerline contact; shifting winds trapped firefighter engine in zero visibility; Daniel Lyon survived with 60-65% burns; fire reached Twisp outskirts within hours; part of Okanogan Complex"},
            {"name": "Carlton Complex", "year": 2014, "acres": 256108, "details": "Fires ignited near Twisp and burned south; town threatened from multiple directions; evacuations ordered; 353 homes destroyed across complex; fire behavior exceeded all predictions"},
            {"name": "Okanogan Complex (broader)", "year": 2015, "acres": 304782, "details": "Twisp River Fire was component of larger complex; 5 fires burning simultaneously; forced evacuations of Twisp and surrounding areas; worst fire season in WA history"},
            {"name": "Cub Creek Fire", "year": 2021, "acres": 2000, "details": "Level 3 evacuations in Twisp River area; rapid response prevented structure loss; demonstrated persistent vulnerability of Twisp River corridor"},
        ],
        "evacuation_routes": [
            {"route": "SR 153 south to Pateros / US 97", "direction": "S", "lanes": 2, "bottleneck": "Primary route but 30 miles through narrow Methow Valley to Pateros; single 2-lane road; fire can close valley simultaneously", "risk": "During Carlton Complex (2014), this entire valley was on fire; route passes through burned area; Pateros was destroyed at the end of this road"},
            {"route": "SR 20 north to Winthrop, then east to Okanogan", "direction": "N/E", "lanes": 2, "bottleneck": "Must pass through Winthrop (7 mi) then over Loup Loup Pass; 2-lane mountain roads; Winthrop itself may be threatened", "risk": "Route through another fire-vulnerable town; Loup Loup Pass in fire-prone forest; 2015 Okanogan Complex threatened this route"},
            {"route": "Twisp River Road west", "direction": "W", "lanes": 2, "bottleneck": "DEAD END into national forest; narrow winding road; becomes a trap; SITE OF 2015 FIREFIGHTER FATALITIES", "risk": "EXTREME: This is the exact road where 3 firefighters died attempting to flee the 2015 fire; no exit; DO NOT evacuate west"},
            {"route": "SR 20 west (seasonal) via Winthrop", "direction": "W", "lanes": 2, "bottleneck": "Must drive north to Winthrop first, then west; SR 20 closed Nov-April; adds 20+ miles and passes through fire zones", "risk": "Not available during shoulder season; extremely indirect route; dependent on Winthrop being accessible"},
        ],
        "fire_spread_characteristics": {
            "primary_wind_regime": "Twisp River valley creates a wind funnel effect at the confluence with Methow Valley; afternoon upvalley winds 15-25 mph; synoptic events produce erratic wind shifts as Twisp River drainage interacts with main valley flow; foehn-type east winds create extreme fire weather; the 2015 fatal fire was characterized by strong, shifting winds that changed direction without warning",
            "critical_corridors": [
                "Twisp River drainage — wind funnel at valley mouth; 2015 fatal fire spread through this corridor; dense forest fuels",
                "Methow Valley main axis — north-south fire corridor; connects Twisp to both Winthrop and Pateros fire zones",
                "Buttermilk Creek / eastern slopes — steep terrain above town; afternoon heating drives upslope fire toward ridgeline above residences",
                "Beaver Creek area — northwest approach through mixed forest/grassland; connects to broader Okanogan fire landscape"
            ],
            "rate_of_spread_potential": "Extreme: 2015 Twisp River Fire grew from ignition to 7,231 acres in 18 hours; wind-driven crown fire in Twisp River valley at 2-3 mph; fire reached town outskirts from 5+ miles up-valley in single burning period; valley convergence zone creates unpredictable wind shifts that can redirect fire toward town without warning",
            "spotting_distance": "1-3 miles; 2015 fire demonstrated long-range spotting from crown fire in Twisp River drainage; embers lofted by convergence-zone updrafts; cross-ridge spotting from Methow Valley fires into Twisp River drainage and vice versa"
        },
        "infrastructure_vulnerabilities": {
            "water_system": "Town of Twisp water from wells; limited storage capacity; rural properties on individual wells dependent on power for pumps; fire demand during simultaneous structure protection can exceed system capacity; no redundant supply",
            "power": "Okanogan County PUD; overhead lines through forested terrain were the CAUSE of the 2015 Twisp River Fire (tree-to-powerline contact); extensive line exposure to fire damage; week+ outages during major fires; limited backup generation in town",
            "communications": "Limited cell coverage (single tower area); 2015 fire caused communication failures during critical period; firefighters reported radio dead zones in Twisp River valley; no redundant communication paths; terrain blocks signals in side drainages",
            "medical": "No hospital in Twisp; Aero Methow Rescue (volunteer EMS); nearest hospital is Mid-Valley Hospital in Omak (40 mi east) or Three Rivers Hospital in Brewster (50 mi south); medical helicopter operations impossible during active fire/smoke; Port Field Airport (WS87) for fixed-wing only"
        },
        "demographics_risk_factors": {
            "population": 992,
            "seasonal_variation": "Summer tourism doubles population; arts festivals and outdoor recreation bring visitors; Methow Valley trail system draws hikers/bikers; winter ski tourism (Methow Valley Nordic ski area) brings more manageable numbers",
            "elderly_percentage": "~22% over 65; artist/retiree community character; rural properties with long access roads and limited mobility options",
            "mobile_homes": "Some manufactured housing on town edges; older units; limited defensible space; rural manufactured homes in Twisp River corridor in extreme risk zone",
            "special_needs_facilities": "No hospital; limited medical facilities; TwispWorks community campus serves as informal gathering point; Methow Valley School District facilities in Twisp; elderly and disabled residents in remote valley properties with single-road access"
        }
    },

    # =========================================================================
    # 2. WENATCHEE, WA — East Cascades city, 2015 Sleepy Hollow Fire
    # =========================================================================
    "wenatchee_wa": {
        "center": [47.4235, -120.3103],
        "terrain_notes": (
            "Wenatchee (pop 35,508) is the largest city in north-central Washington, located at "
            "the confluence of the Wenatchee and Columbia Rivers at the eastern base of the "
            "Cascade Range. The city sits in a broad valley (elev ~630-700 ft at river level) "
            "surrounded by steep, sage-covered hillsides to the west and south that rise sharply "
            "1,500-2,500 ft above the valley floor. These west-facing hillsides, covered in "
            "cheatgrass, sagebrush, bitterbrush, and scattered ponderosa pine, form a classic "
            "WUI interface where residential development has pushed directly into high-hazard "
            "fuels. The Cascade gap-wind phenomenon is pronounced here: as marine air pushes "
            "through Cascade passes (particularly Blewett Pass and Stevens Pass corridors), it "
            "accelerates via the Bernoulli effect as it descends the eastern slopes, reaching "
            "30-40 mph in the Wenatchee Valley. These desiccating east-slope winds combine with "
            "triple-digit summer temperatures and single-digit humidity to create extreme fire "
            "weather. The 2015 Sleepy Hollow Fire demonstrated this vulnerability when a wind-"
            "driven grass fire raced 3 miles from open rangeland into dense residential areas in "
            "hours, destroying 28 homes and 3 commercial warehouses. The fire started in open "
            "sage west of town and burned directly into 'a pretty dense urban interface area,' "
            "forcing evacuation of 1,000+ residents. Wenatchee's role as a regional commercial "
            "and medical hub means fire impacts cascade through the broader region."
        ),
        "key_features": [
            {"name": "Western hillsides (Sleepy Hollow area)", "bearing": "W", "type": "terrain/WUI", "notes": "Steep sage/grass slopes where 2015 fire originated; dense residential development extends into flashy fuels; south/west-facing aspects maximize solar heating"},
            {"name": "Columbia River corridor", "bearing": "E", "type": "terrain/transport", "notes": "Major north-south wind corridor; US 2/97 runs along river; provides some firebreak but wind channeling"},
            {"name": "Wenatchee River corridor", "bearing": "W", "type": "terrain", "notes": "River valley extends west toward Leavenworth; gap wind corridor from Cascade crest"},
            {"name": "Saddle Rock / Number 2 Canyon", "bearing": "S", "type": "terrain", "notes": "Prominent ridgeline south of town; fire can approach from Number 2 Canyon drainage; communication towers on ridge"},
            {"name": "Downtown / commercial core", "bearing": "center", "type": "urban", "notes": "Regional commercial hub at river level; relatively protected by flat terrain but smoke impacts severe"},
        ],
        "elevation_range_ft": [630, 3100],
        "wui_exposure": "extreme",
        "historical_fires": [
            {"name": "Sleepy Hollow Fire", "year": 2015, "acres": 3000, "details": "Started June 28 in grass/sage 3 mi W of town; wind-driven (gusts 30+ mph) with triple-digit temps; destroyed 28 homes and 3 commercial warehouses; 1,000+ evacuated; burned into dense residential WUI; arson — juvenile arrested"},
            {"name": "Number 2 Canyon Fire", "year": 2012, "acres": 400, "details": "Fast-moving grass fire in canyon south of town; threatened homes on south benchlands; demonstrated vulnerability of southern approach"},
            {"name": "Wenatchee hillside fires", "year": 2024, "acres": 150, "details": "Recurring grass fires on western slopes demonstrate ongoing ignition risk from human activity and equipment"},
        ],
        "evacuation_routes": [
            {"route": "US 2/97 north along Columbia River", "direction": "N", "lanes": 4, "bottleneck": "4-lane divided highway provides best capacity; narrows to 2 lanes north of East Wenatchee", "risk": "Route parallels fire-prone hillsides for first 5 miles; smoke can reduce visibility on river bridge"},
            {"route": "US 2 west to Leavenworth/Stevens Pass", "direction": "W", "lanes": 2, "bottleneck": "2-lane highway through Tumwater Canyon; single-point failure at canyon narrows; historically closed by fire", "risk": "Passes through heavily forested canyon with no alternate routes for 25+ miles"},
            {"route": "US 97A south to Ellensburg via Blewett Pass", "direction": "S", "lanes": 2, "bottleneck": "Mountainous 2-lane road over Blewett Pass (4,102 ft); slow-moving traffic with trucks", "risk": "Pass road through dense forest; fire or landslide closure creates 100+ mile detour"},
            {"route": "SR 285 / US 2 east to East Wenatchee", "direction": "E", "lanes": 4, "bottleneck": "Columbia River bridge is single point of failure; 2 bridges available but converge at interchanges", "risk": "Bridge evacuation bottleneck if fire threatens from west simultaneously; East Wenatchee has own fire exposure"},
        ],
        "fire_spread_characteristics": {
            "primary_wind_regime": "Cascade gap winds (Bernoulli effect) accelerate through Stevens Pass and Blewett Pass corridors, reaching 30-40 mph at valley floor; diurnal upslope/downslope cycle on western hillsides; east wind events less common but devastating when they occur",
            "critical_corridors": [
                "Western benchlands (Sleepy Hollow) — grass/sage slopes funnel fire directly into residential areas within 30 min",
                "Number 2 Canyon — south-facing drainage channels fire uphill into developed ridgeline",
                "Wenatchee River corridor — gap wind acceleration zone connecting Cascade crest to valley",
                "Squilchuck Creek drainage — southwest approach through mixed fuels to south Wenatchee"
            ],
            "rate_of_spread_potential": "Extreme in grass/sage (3-6 mph with 20+ ft flame lengths during wind events); the 2015 Sleepy Hollow Fire covered 3 miles of sage into residential areas in ~4 hours; ponderosa stringers on hillsides enable crown fire runs",
            "spotting_distance": "0.5-1.5 miles in sage/grass with wind; bark transport from ponderosa can exceed 0.5 mile; downslope rollout of burning material on steep slopes extends effective spotting range"
        },
        "infrastructure_vulnerabilities": {
            "water_system": "City of Wenatchee water from Columbia River treatment plant and wells; system adequate for normal demand but simultaneous structure protection across the WUI strains hydrant pressure in upper-elevation neighborhoods; 2015 fire revealed pressure drops in hillside areas",
            "power": "Chelan County PUD hydroelectric; above-ground distribution extensively damaged in 2015 fire; hillside transformer stations in high-exposure areas; limited underground infrastructure in WUI zones",
            "communications": "Cell towers on Saddle Rock and western ridges vulnerable to fire; 2015 Sleepy Hollow Fire degraded communications during critical evacuation period; county emergency notification system (CodeRED) dependent on cell/internet",
            "medical": "Central Washington Hospital (Level II trauma, 210 beds) — regional medical center serving 250,000+ across 5 counties; hospital itself not in direct fire path but smoke impacts air quality; medical helicopter ops limited by smoke; loss of this facility cascades across entire region"
        },
        "demographics_risk_factors": {
            "population": 35508,
            "seasonal_variation": "Apple harvest season (Aug-Oct) brings 5,000-10,000 seasonal agricultural workers, many in temporary housing; summer recreation increases population; regional hub draws workers from surrounding communities",
            "elderly_percentage": "~15% over 65; multiple senior living facilities on benchlands in WUI-adjacent areas",
            "mobile_homes": "Multiple manufactured home parks, particularly on east and south edges; many lack defensible space; older units with combustible siding and roofing",
            "special_needs_facilities": "Central Washington Hospital; multiple assisted living facilities; seasonal worker camps with language barriers for fire notification (Spanish-speaking workforce ~30%); homeless population along river corridor"
        }
    },

    # =========================================================================
    # 5. WINTHROP, WA — Methow Valley, Carlton Complex
    # =========================================================================
    "winthrop_wa": {
        "center": [48.4793, -120.1861],
        "terrain_notes": (
            "Winthrop (pop 504) is a small Western-themed tourist town at the confluence of the "
            "Methow and Chewuch Rivers in the upper Methow Valley, surrounded by the Okanogan-"
            "Wenatchee National Forest. The town sits at approximately 1,765 ft elevation in a "
            "relatively broad portion of the valley, but is hemmed in by steep, forested mountain "
            "slopes rising to 7,000-8,500 ft on all sides. The Methow Valley runs roughly north-"
            "south for 50 miles from Mazama to Pateros, forming a natural fire corridor that "
            "channels wind and fire along its length. Highway 20 (North Cascades Highway) is the "
            "sole east-west route, but it is CLOSED from mid-November to mid-April due to snow, "
            "leaving SR 153 south through Twisp and Pateros as the only year-round access. During "
            "the 2014 Carlton Complex — the largest fire in Washington history at 256,108 acres — "
            "lightning ignited four fires near Carlton, Twisp, and Winthrop on July 14. Hot winds "
            "turned them into a firestorm on July 17 that raced 25 miles south to Pateros, "
            "destroying 353 homes. The fire approached Winthrop from multiple directions. The "
            "valley's fire ecology includes dry ponderosa pine/Douglas fir forests at lower "
            "elevations transitioning to dense mixed conifer at higher elevations, with extensive "
            "grass and shrub understory. Decades of fire suppression have created heavy fuel "
            "loading. The town's economy depends entirely on tourism and recreation, with summer "
            "population increasing 5-10x."
        ),
        "key_features": [
            {"name": "Methow River valley corridor", "bearing": "N-S", "type": "terrain", "notes": "50-mile fire corridor from Mazama to Pateros; channels wind and fire; 2014 Carlton Complex raced entire length in 3 days"},
            {"name": "Chewuch River valley", "bearing": "N", "type": "terrain", "notes": "North-trending valley with dense forest; fire approach from Pasayten Wilderness; Chewuch Road provides limited access to dispersed residences"},
            {"name": "North Cascades Highway (SR 20)", "bearing": "W", "type": "transport", "notes": "Sole westward route; CLOSED Nov-April; when open, provides access to Skagit Valley but crosses remote mountain terrain"},
            {"name": "Goat Peak / Sun Mountain area", "bearing": "W/SW", "type": "terrain", "notes": "Steep, south-facing slopes above town; Sun Mountain Lodge and resort community in extreme WUI position"},
            {"name": "Methow Valley floor (Carlton/Benson Creek)", "bearing": "S", "type": "terrain", "notes": "Open grassland and rangeland south of town; route of Carlton Complex fire spread; flashy fuels connect to Twisp"},
        ],
        "elevation_range_ft": [1700, 8500],
        "wui_exposure": "extreme",
        "historical_fires": [
            {"name": "Carlton Complex", "year": 2014, "acres": 256108, "details": "Largest WA fire in recorded history; 4 lightning-caused fires merged July 17; destroyed 353 homes; $98M damage; firestorm raced 25 mi from Winthrop area to Pateros; hot winds (gusts 40+ mph) created 100+ ft flame lengths"},
            {"name": "Okanogan Complex", "year": 2015, "acres": 304782, "details": "Surpassed Carlton Complex acreage (but was multiple fires); 5 lightning-caused fires; forced evacuations of Twisp and Winthrop; included fatal Twisp River Fire"},
            {"name": "Cedar Creek/Cub Creek fires", "year": 2021, "acres": 8000, "details": "Forced Level 3 (GO NOW) evacuations in Methow Valley; demonstrated continued fire vulnerability; rapid response prevented structure loss"},
            {"name": "Crescent Mountain Fire", "year": 2018, "acres": 3600, "details": "Burned northwest of Winthrop; closed portions of SR 20; threatened Mazama community"},
        ],
        "evacuation_routes": [
            {"route": "SR 20 east to Okanogan/Omak", "direction": "E", "lanes": 2, "bottleneck": "2-lane highway through Loup Loup Pass (4,020 ft); winding mountain road with limited capacity; fire can close pass", "risk": "Route passes through fire-prone pine forest; 2015 Okanogan Complex threatened this route; only viable year-round eastern exit"},
            {"route": "SR 20 west to Skagit Valley (seasonal)", "direction": "W", "lanes": 2, "bottleneck": "CLOSED mid-November to mid-April; when open, remote mountain highway with no services for 75 miles; Washington/Rainy Pass at 5,477 ft", "risk": "Not available during shoulder fire season (Oct-Nov); closures for any reason eliminate western escape; extremely remote"},
            {"route": "SR 153 south through Twisp to Pateros", "direction": "S", "lanes": 2, "bottleneck": "Primary year-round route but passes directly through Twisp (another fire-vulnerable town) and down the Methow Valley fire corridor to Pateros (destroyed in 2014)", "risk": "EXTREME: During Carlton Complex, this entire corridor was simultaneously on fire; fleeing south meant driving toward the fire"},
            {"route": "Chewuch Road north", "direction": "N", "lanes": 2, "bottleneck": "Dead-end road into national forest; no through-route; leads to dispersed residences and campgrounds", "risk": "Becomes a trap; no exit; fire approach from any direction blocks retreat"},
        ],
        "fire_spread_characteristics": {
            "primary_wind_regime": "Valley-channeled winds from north or south at 15-30 mph; synoptic events produce dry east winds (foehn-type) descending Cascade eastern slopes at 30-50 mph; thermal belt effects create overnight warming and drying on mid-slope positions; convective column-generated winds during large fires exceed 50 mph",
            "critical_corridors": [
                "Methow Valley north-south axis — 50-mile fire corridor from Mazama to Pateros; Carlton Complex demonstrated full-length fire run",
                "Chewuch River drainage — north-south corridor; fire approach from Pasayten Wilderness",
                "Twisp River drainage — east-west corridor connecting to main valley; site of 2015 fatal fire",
                "Benson Creek / Carlton area — open grassland/sage south of Winthrop; flashy fuels connect town to valley fire runs"
            ],
            "rate_of_spread_potential": "EXTREME: Carlton Complex traveled 25 miles in one burning period (July 17, 2014); crown fire in dense conifer at 2-4 mph; grass/sage at valley floor at 5-8 mph; terrain-driven runs on steep slopes can exceed 5 mph; fire whirls documented during Carlton Complex",
            "spotting_distance": "2-5 miles documented during Carlton Complex; convective column lofted embers across ridges; cross-valley spotting ignited fires on opposite slopes simultaneously; ember showers reported in Winthrop during 2014 and 2015 fires"
        },
        "infrastructure_vulnerabilities": {
            "water_system": "Town of Winthrop water from wells and Methow River; limited storage capacity; fire demand can exceed system capacity for extended operations; rural properties on individual wells lose water if power fails",
            "power": "Okanogan County PUD; extensive above-ground lines through forested terrain; Carlton Complex destroyed miles of power infrastructure; weeks-long outages common during major fires; limited backup generation",
            "communications": "Cell coverage limited to valley floor (single AT&T/Verizon tower); fire can destroy repeater sites on mountain peaks; 2014 Carlton Complex caused communication blackouts; satellite phones needed for backcountry; Methow Valley News serves as community information hub",
            "medical": "Aero Methow Rescue (volunteer EMS); nearest hospital is Mid-Valley Hospital in Omak (55 mi east) or Central Washington Hospital in Wenatchee (95 mi south); medical helicopter operations impossible during active fire/smoke; 911 response times exceed 20 min for rural areas"
        },
        "demographics_risk_factors": {
            "population": 504,
            "seasonal_variation": "EXTREME: Summer population increases 5-10x to 3,000-5,000; vacation rentals, campgrounds, and Sun Mountain Lodge bring tourists unfamiliar with fire risk; winter population drops with SR 20 closure; wildfire season (July-Sept) coincides exactly with peak tourism",
            "elderly_percentage": "~25% over 65; significant retiree/second-home population; remote rural properties with long driveways and limited mobility",
            "mobile_homes": "Scattered manufactured housing in valley; some without defensible space; older units with combustible materials; rural sites with limited road access",
            "special_needs_facilities": "No hospital; limited medical facilities; elderly residents in remote properties; seasonal visitors with no local knowledge; backcountry recreationists (hikers, campers) difficult to notify and evacuate"
        }
    },

    # =========================================================================
    # IDAHO (10 cities)
    # =========================================================================

    # =========================================================================
    # 1. BOISE, ID — Enhanced (foothills WUI, Boise Front)
    # =========================================================================
    "boise_id": {
        "center": [43.6150, -116.2023],
        "terrain_notes": (
            "Boise (pop ~240,000) sits at the interface of the Snake River Plain and the Boise "
            "Front — a dramatic escarpment of foothill ridges rising 2,500-3,000 ft above the city "
            "floor within 2-3 miles. The Boise Front extends ~30 miles along the city's northern "
            "edge, from Lucky Peak Dam on the east to Eagle on the west, creating one of the most "
            "extensive wildland-urban interface zones in the American West. Subdivision development "
            "has pushed deep into foothill drainages including Hulls Gulch, Crane Creek, Dry Creek, "
            "Bogus Basin Road corridor, and the Table Rock/Warm Springs Mesa area. The terrain is "
            "characterized by steep, south-facing grass and sagebrush slopes that cure rapidly by "
            "late June, interspersed with draws that channel both wind and fire upslope. The "
            "1992 Foothills Fire (257,000 acres), 1996 8th Street Fire (15,300 acres), 2016 Table "
            "Rock Fire (2,600 acres), and 2024 Valley Fire (9,904 acres) all demonstrate the "
            "recurring ignition risk. Ada County's Community Wildfire Protection Plan identifies "
            "seven Firewise Communities and has invested over $1M in fuel treatments, but the pace "
            "of WUI development continues to outstrip mitigation. Humans cause >80% of Treasure "
            "Valley wildfires. The BLM manages most foothills land, complicating jurisdictional "
            "response with Boise Fire Department, Ada County, and federal agencies all overlapping."
        ),
        "key_features": [
            {"name": "Table Rock", "bearing": "ENE", "type": "landmark",
             "notes": "Iconic sandstone butte above city; 2016 fire origin. Steep grass slopes funnel fire toward Warm Springs residential area."},
            {"name": "Boise Front Ridgeline", "bearing": "N", "type": "terrain",
             "notes": "30-mile escarpment rising 2,500-3,000 ft above city. South-facing slopes cure early, creating fire-receptive fuels by late June."},
            {"name": "Bogus Basin Road Corridor", "bearing": "NNE", "type": "corridor",
             "notes": "Primary access to Bogus Basin ski area. Narrow two-lane road through dense WUI development in timber/brush transition zone."},
            {"name": "Hulls Gulch / Camelsback", "bearing": "N", "type": "drainage",
             "notes": "Deep drainage opening directly into North End residential neighborhood. Grass/sage fuels channel upslope winds into city."},
            {"name": "Lucky Peak Reservoir", "bearing": "E", "type": "water",
             "notes": "Dam and reservoir at east end of Boise Front. Highway 21 corridor to Idaho City passes through extreme fire terrain."},
            {"name": "Eagle Foothills", "bearing": "NW", "type": "terrain",
             "notes": "Rapidly developing WUI on western Boise Front. New subdivisions with limited egress into cheatgrass-dominated rangeland."},
        ],
        "elevation_range_ft": [2700, 7590],
        "wui_exposure": "extreme",
        "historical_fires": [
            {"name": "Foothills Fire", "year": 1992, "acres": 257000,
             "details": "Massive range/forest fire across Boise Front. Burned for two weeks. Demonstrated catastrophic potential of foothills terrain."},
            {"name": "8th Street Fire", "year": 1996, "acres": 15300,
             "details": "Started by police officer firing tracer rounds at training range. Burned for 96 hours across Boise Foothills. Transformative event for local fire agencies."},
            {"name": "Table Rock Fire", "year": 2016, "acres": 2600,
             "details": "Human-caused (fireworks) on June 29. Destroyed 1 home that family had occupied 60+ years. Burned native grassland directly above east Boise neighborhoods."},
            {"name": "Valley Fire", "year": 2024, "acres": 9904,
             "details": "Caused by Idaho Power line contacting ground on Oct 4. Burned in east Boise foothills along Hwy 21 corridor. 79% contained, no structures lost but threatened homes in SE Boise."},
        ],
        "evacuation_routes": [
            {"route": "I-84 West", "direction": "W toward Nampa/Caldwell", "lanes": 6,
             "bottleneck": "Meridian interchange congestion; shared with normal commuter traffic",
             "risk": "Smoke from foothill fires can reduce visibility on I-84 connector routes"},
            {"route": "I-84 East", "direction": "E toward Mountain Home", "lanes": 4,
             "bottleneck": "Single corridor through canyon east of city; Lucky Peak Dam area",
             "risk": "Highway 21 junction directly in fire-prone terrain"},
            {"route": "Highway 55 North", "direction": "N toward Horseshoe Bend/McCall", "lanes": 2,
             "bottleneck": "Narrow canyon along Payette River; single road north",
             "risk": "Passes through extreme fire terrain in Boise NF; historically closed by fires"},
            {"route": "Highway 21 East", "direction": "NE toward Idaho City/Stanley", "lanes": 2,
             "bottleneck": "Winding mountain highway through Boise NF; frequently closed by wildfire",
             "risk": "2024 Valley Fire burned along this corridor; Pioneer Fire closed it in 2016"},
        ],
        "fire_spread_characteristics": {
            "primary_wind_regime": (
                "Diurnal upslope/downslope cycle dominates. Afternoon SW winds push fire uphill into "
                "foothills at 15-25 mph. Nocturnal drainage winds reverse flow but are typically lighter. "
                "East wind events (rare but dangerous) drive fire downslope directly into populated areas. "
                "Thermal belt effects keep mid-slope fuels warm and dry overnight."
            ),
            "critical_corridors": [
                "Hulls Gulch — direct drainage into North End neighborhoods",
                "Table Rock / Warm Springs — steep grass slopes above dense residential",
                "Bogus Basin Road — timber/brush corridor with WUI development on both sides",
                "Dry Creek — Eagle foothills drainage into rapidly developing subdivisions",
                "Highway 21 corridor — Lucky Peak to Idaho City, extreme terrain fire runs"
            ],
            "rate_of_spread_potential": (
                "Grass/sage fuels on south-facing slopes support 3-5 mph head fire spread in "
                "moderate winds. Extreme conditions (as in 1992 Foothills Fire) can produce "
                "rates exceeding 6-8 mph with 100+ ft flame lengths in continuous grass. Cheatgrass "
                "invasion has increased fine fuel continuity across the entire Boise Front."
            ),
            "spotting_distance": (
                "0.25-0.5 miles typical in grass/sage; longer in timber transition zones above "
                "5,000 ft. Ember transport into residential areas is the primary home ignition mechanism — "
                "wind-blown embers are the main cause of structure ignition per Ada County CWPP."
            ),
        },
        "infrastructure_vulnerabilities": {
            "water_system": (
                "Municipal system adequate for urban core but foothill subdivisions on smaller mains "
                "and some on private wells. Hydrant coverage thins rapidly above 3,200 ft elevation. "
                "Pressure issues in uphill subdivisions during high-demand firefighting operations."
            ),
            "power": (
                "Idaho Power overhead lines throughout foothills — 2024 Valley Fire caused by power "
                "line contact with ground. Wind events down lines regularly. Transformer fires can "
                "become ignition sources. Grid vulnerable to multi-point failure during large fires."
            ),
            "communications": (
                "Good cellular coverage in city and lower foothills. Gaps in deeper canyons (Hulls "
                "Gulch, Dry Creek upper reaches). CodeRED emergency notification system deployed by "
                "Ada County. Amateur radio backup networks established post-Table Rock Fire."
            ),
            "medical": (
                "St. Luke's Boise Medical Center (Level II Trauma), Saint Alphonsus Regional Medical "
                "Center, and VA Medical Center provide robust capacity. Medical infrastructure not a "
                "limiting factor for Boise proper, but access roads to foothill areas can be cut."
            ),
        },
        "demographics_risk_factors": {
            "population": 240000,
            "seasonal_variation": (
                "Year-round metro population ~770K (Treasure Valley). Summer recreation increases "
                "foothill trail usage dramatically — Boise River Greenbelt and Ridge to Rivers trail "
                "system see 1M+ annual visits, concentrating people in fire-prone terrain."
            ),
            "elderly_percentage": "~14% (65+), higher in some foothill neighborhoods",
            "mobile_homes": (
                "Limited in city proper but mobile home parks exist in Boise Bench and Garden City "
                "areas. More prevalent in unincorporated Ada County foothill fringe areas."
            ),
            "special_needs_facilities": (
                "Multiple assisted living facilities, hospitals, and schools in potential smoke "
                "impact zone. Boise State University campus (24,000 students) in Boise River "
                "corridor downwind of foothills."
            ),
        },
    },

    # =========================================================================
    # 5. CASCADE, ID — New
    # =========================================================================
    "cascade_id": {
        "center": [44.5163, -116.0418],
        "terrain_notes": (
            "Cascade (pop ~1,000) is the county seat of Valley County, situated at 4,780 ft "
            "elevation on the southeast shore of Lake Cascade (formerly Cascade Reservoir) in "
            "Long Valley. The town sits at the junction of the North Fork of the Payette River "
            "and Lake Cascade, between the West Mountain range to the west and the Boise National "
            "Forest to the east. Highway 55 (Payette River Scenic Byway) is the primary "
            "transportation artery, connecting Cascade to Boise (75 miles south) and McCall "
            "(30 miles north). The USFS Southwest Idaho Wildfire Crisis Landscape Project "
            "identifies Cascade as one of 14 community cores with elevated transboundary wildfire "
            "exposure. The surrounding 1.7-million-acre landscape encompasses 424,000 acres of "
            "the Boise NF and 505,000 acres of the Payette NF. Prescribed fire projects have "
            "treated areas 4-10 miles from town (Willow South 228 acres, Moore Moths 148 acres, "
            "Lost Horse 173 acres), but the scale of treatment is dwarfed by the scale of risk. "
            "Tamarack Resort (12 miles west on West Mountain) brings seasonal population surges "
            "and was forced to close by the 2025 Rock Fire."
        ),
        "key_features": [
            {"name": "Lake Cascade", "bearing": "NW", "type": "water",
             "notes": "Large reservoir (28,000 acres when full) formed by Cascade Dam. Provides significant natural firebreak to north and west of town."},
            {"name": "Cascade Dam", "bearing": "N", "type": "infrastructure",
             "notes": "Bureau of Reclamation dam on North Fork Payette River. Critical infrastructure — damage would impact downstream communities."},
            {"name": "West Mountain", "bearing": "W", "type": "terrain",
             "notes": "7,500+ ft mountain range west of lake. Forested slopes with Tamarack Resort. 2025 Rock Fire burned on these slopes."},
            {"name": "Thunder Mountain", "bearing": "E", "type": "terrain",
             "notes": "Boise NF backcountry east of Cascade. Remote, unmanaged fuels. Source area for fires threatening from east."},
            {"name": "North Fork Payette River", "bearing": "S", "type": "water",
             "notes": "World-class kayaking river. Highway 55 follows this corridor south to Banks — narrow canyon, fire-prone."},
            {"name": "Warm Lake Road", "bearing": "E", "type": "corridor",
             "notes": "Access to Warm Lake area east of Cascade. 2007 Cascade Complex fires burned in this drainage."},
        ],
        "elevation_range_ft": [4780, 7600],
        "wui_exposure": "high",
        "historical_fires": [
            {"name": "Cascade Complex", "year": 2007, "acres": 300000,
             "details": "Multiple fires in Boise/Payette NFs. Extreme behavior near Warm Lake east of Cascade. 300-ft flame lengths, 5-7 mile spotting confirmed. Threatened Cascade from multiple directions."},
            {"name": "Rock Fire (nearby)", "year": 2025, "acres": 2844,
             "details": "Lightning-caused fire near Tamarack Resort on West Mountain. Forced resort closure and Level 2 evacuations for west Lake Cascade residents. 700 personnel deployed."},
            {"name": "Four Corners Fire", "year": 2024, "acres": 7500,
             "details": "Burned on border of Payette and Boise NFs near Cascade area. Part of the extreme 2024 Idaho fire season."},
        ],
        "evacuation_routes": [
            {"route": "Highway 55 South", "direction": "S toward Banks/Boise", "lanes": 2,
             "bottleneck": "Payette River canyon — narrow, winding, 75 miles to Boise. Single paved route south.",
             "risk": "Canyon terrain channels fire across highway. Rock slides and avalanche zones. Winter closures."},
            {"route": "Highway 55 North", "direction": "N toward McCall/New Meadows", "lanes": 2,
             "bottleneck": "30 miles to McCall. Road passes through forested terrain with fire exposure.",
             "risk": "Fire on West Mountain or east-side Boise NF can threaten this route."},
            {"route": "Warm Lake Road East", "direction": "E toward Landmark/Idaho backcountry", "lanes": 1,
             "bottleneck": "Unpaved, remote, dead-end. Leads into fire source terrain.",
             "risk": "Not a viable evacuation route — leads to Warm Lake area (2007 Cascade Complex origin)."},
        ],
        "fire_spread_characteristics": {
            "primary_wind_regime": (
                "Long Valley acts as a wind corridor with afternoon southerly thermal winds and "
                "nighttime northerly drainage. Thunderstorm outflows from Boise NF to the east "
                "can produce sudden wind shifts. West Mountain creates its own mesoscale wind "
                "patterns, with upslope heating driving afternoon fires uphill toward Tamarack."
            ),
            "critical_corridors": [
                "Warm Lake drainage east — source area for 2007 Cascade Complex",
                "West Mountain slopes — fire here threatens west Lake Cascade and Tamarack Resort",
                "North Fork Payette canyon south — fire cuts sole highway to Boise",
                "Poison Creek drainage — approaches town from southeast through Boise NF",
            ],
            "rate_of_spread_potential": (
                "Mixed sagebrush/conifer fuels support 2-4 mph spread in grass/sage, 1-3 mph in "
                "timber. Lake Cascade provides significant natural firebreak on west/north but town "
                "is exposed from east and south. The 2007 Cascade Complex showed that fires in "
                "this terrain can make multi-thousand-acre runs in a single day."
            ),
            "spotting_distance": (
                "1-3 miles in typical conditions; 2007 Cascade Complex confirmed 5-7 miles. Long "
                "Valley terrain amplifies convective columns, increasing long-range spotting risk."
            ),
        },
        "infrastructure_vulnerabilities": {
            "water_system": (
                "Small municipal system serves town core. Abundant raw water from Lake Cascade "
                "but treatment and distribution capacity limited. Rural-residential areas on wells."
            ),
            "power": (
                "Idaho Power distribution through forested corridors. Limited redundancy. Extended "
                "outages likely during major fire events. No backup generation for most facilities."
            ),
            "communications": (
                "Cellular coverage adequate in town, poor in surrounding forest. Valley County "
                "emergency alerts via CodeRED. Radio communications limited by terrain."
            ),
            "medical": (
                "Cascade Medical Center — small critical access facility, basic ER. Nearest hospital "
                "is St. Luke's McCall (30 miles north). Major trauma requires transport to Boise "
                "(75 miles south). Air ambulance weather-dependent."
            ),
        },
        "demographics_risk_factors": {
            "population": 1005,
            "seasonal_variation": (
                "Year-round pop ~1,000. Summer tourism and Tamarack Resort operations can double "
                "or triple population. Winter ski season at Tamarack adds another surge. Many "
                "vacation/second homes around Lake Cascade are seasonally occupied."
            ),
            "elderly_percentage": "~22% (65+), higher than state average for rural community",
            "mobile_homes": (
                "Significant manufactured/mobile home presence in and around town. Lower property "
                "values attract fixed-income residents. Higher vulnerability structures."
            ),
            "special_needs_facilities": (
                "Cascade Medical Center. Cascade Elementary and Jr-Sr High School. Limited "
                "assisted living. Small, close-knit community with mutual-aid social networks "
                "but limited institutional capacity for mass care."
            ),
        },
    },

    # =========================================================================
    # 10. FEATHERVILLE / PINE, ID — New
    # =========================================================================
    "featherville_pine_id": {
        "center": [43.5050, -115.3050],
        "terrain_notes": (
            "Featherville (pop ~150) and Pine (pop ~60) are small, remote communities along the "
            "South Fork of the Boise River in Elmore County, 105 miles northeast of Boise. "
            "Featherville sits at approximately 4,964 ft elevation. The two towns, separated by "
            "10 miles, occupy a narrow river valley surrounded by the Boise National Forest with "
            "steep, forested mountain slopes on all sides. The area has ~450 homes, with about "
            "half occupied year-round and half serving as summer/weekend retreats. This community "
            "has been evacuated repeatedly: the 2012 Trinity Ridge Fire (138,965 acres, "
            "human-caused from ATV fire) burned just 2 miles from Featherville; the 2013 Elk "
            "Complex Fire (130,000+ acres, lightning-caused) destroyed 38 residences and over "
            "a dozen homes directly in Pine and Featherville. It was the second consecutive year "
            "of mandatory evacuation. Anderson Ranch Reservoir to the south provides recreation "
            "access but the road network is limited to a single paved route (Pine-Featherville "
            "Road connecting to Highway 20 near Fairfield or Forest Road to Idaho City)."
        ),
        "key_features": [
            {"name": "South Fork Boise River", "bearing": "E-W", "type": "water",
             "notes": "River flows through both communities. USGS gauge station at Featherville. Canyon terrain with fire-prone slopes above."},
            {"name": "Anderson Ranch Reservoir", "bearing": "S", "type": "water",
             "notes": "Large reservoir south of Pine. Recreation destination. Access road is one of few routes in/out."},
            {"name": "Trinity Mountain", "bearing": "NW", "type": "terrain",
             "notes": "Area where 2012 Trinity Ridge Fire originated (ATV fire). 7,000+ ft. Dense conifer forest."},
            {"name": "Elk Mountain Complex", "bearing": "N-NE", "type": "terrain",
             "notes": "Area of 2013 Elk Complex Fire. Lightning-caused. Forest terrain with steep approaches to community."},
            {"name": "Featherville Main Street", "bearing": "local", "type": "community",
             "notes": "Historic mining town — single main street, saloon, motel, cafe. Clustered structures in narrow canyon."},
            {"name": "Boise National Forest", "bearing": "all directions", "type": "forest",
             "notes": "Surrounds communities completely. Dense mixed conifer with fire-adapted ecosystems and heavy fuel loads."},
        ],
        "elevation_range_ft": [4800, 7500],
        "wui_exposure": "extreme",
        "historical_fires": [
            {"name": "Trinity Ridge Fire", "year": 2012, "acres": 138965,
             "details": "Human-caused (ATV caught fire) Aug 3. Burned 2 miles NW of Featherville. Forced evacuation of hundreds. Blackened 228 square miles. 10% contained at peak."},
            {"name": "Elk Complex Fire", "year": 2013, "acres": 130000,
             "details": "Lightning-caused Aug 8. Multiple fires merged. Destroyed 38 residences, a dozen+ homes in Pine and Featherville. Second consecutive year of evacuation. Second-largest active fire in US at peak. 90,249 acres of grass, brush, conifer burned."},
            {"name": "Little Queens Fire", "year": 2018, "acres": 5500,
             "details": "Burned in Boise NF near Featherville area. Continued pattern of annual fire threats."},
        ],
        "evacuation_routes": [
            {"route": "Pine-Featherville Road South", "direction": "S toward Anderson Ranch/Highway 20", "lanes": 2,
             "bottleneck": "Narrow, winding road through forest/canyon. 40+ miles to Highway 20 near Fairfield.",
             "risk": "Fire can cut this road in multiple locations. Primary evacuation route for all 450 homes."},
            {"route": "Forest Road to Idaho City", "direction": "NW toward Idaho City/Boise", "lanes": 1,
             "bottleneck": "Rough forest road, unpaved sections, steep grades. Not suitable for passenger vehicles.",
             "risk": "Passes through Trinity Ridge Fire burn area. Emergency use only."},
            {"route": "South Fork Road East", "direction": "E toward Ketchum (remote)", "lanes": 1,
             "bottleneck": "Extremely rough, seasonal, unpaved. Dead-ends or connects to primitive roads.",
             "risk": "Not a viable evacuation route for general population."},
        ],
        "fire_spread_characteristics": {
            "primary_wind_regime": (
                "Canyon/valley thermal winds similar to other South Fork communities. Afternoon "
                "up-canyon (westerly) winds draw fire from forest toward communities. Evening "
                "drainage winds reverse. Thunderstorm outflows produce the most dangerous conditions "
                "— the 2013 Elk Complex fires were lightning-caused and driven by erratic storm "
                "winds. Canyon constriction at Featherville accelerates wind flow past structures."
            ),
            "critical_corridors": [
                "South Fork Boise River canyon — fire channeled directly through both communities",
                "Trinity Mountain drainage NW — 2012 fire approach direction",
                "Elk Creek drainage NE — 2013 fire approach, multiple drainage fire merger",
                "Pine-Featherville Road corridor — fire along road cuts sole evacuation route",
            ],
            "rate_of_spread_potential": (
                "Dense mixed conifer forest with significant fuel accumulation. Surface fire "
                "1-2 mph, crown fire 2-4 mph in continuous canopy. The 2013 Elk Complex "
                "demonstrated that multiple lightning-ignited fires can merge and produce "
                "simultaneous assaults on the community from multiple directions, overwhelming "
                "suppression capacity."
            ),
            "spotting_distance": (
                "1-3 miles in forested canyon terrain. Canyon updrafts amplify lofting. "
                "Ember showers from ridge-top fires land directly in community due to narrow "
                "canyon geometry. Combustible roof materials on older structures highly receptive."
            ),
        },
        "infrastructure_vulnerabilities": {
            "water_system": (
                "No municipal water system. Individual wells and river drafting. No fire hydrants. "
                "USGS gauge station on South Fork but no firefighting water infrastructure. The "
                "destruction of 38 residences in 2013 demonstrated that water supply is the "
                "critical limiting factor in structure defense."
            ),
            "power": (
                "Idaho Power single-feed distribution through forested terrain. Power poles in "
                "fire corridor. Lines damaged in both 2012 and 2013 fires. Extended outages. "
                "No backup generation. Power loss cascades to water supply failure."
            ),
            "communications": (
                "Extremely limited cellular coverage in canyon terrain. No cell towers in immediate "
                "area. Landline service only for some properties. Emergency notification is "
                "door-to-door and word-of-mouth. Some residents chose to stay during 2013 "
                "evacuations partly due to lack of timely notification."
            ),
            "medical": (
                "No medical facilities. Nearest is Mountain Home (60+ miles) or Boise (105 miles). "
                "Volunteer fire/EMS provides first response. Air ambulance requires clear landing "
                "zone and may be grounded by fire activity/smoke. During 2013 Elk Complex, medical "
                "resources were fully committed to fire operations."
            ),
        },
        "demographics_risk_factors": {
            "population": 210,
            "seasonal_variation": (
                "Combined year-round pop ~210 (Featherville ~150, Pine ~60). Summer recreation "
                "doubles population with vacation homeowners, campers, and Anderson Ranch Reservoir "
                "visitors. About half of 450 homes are summer/weekend retreats — owners may not "
                "receive evacuation notifications or may not know evacuation routes."
            ),
            "elderly_percentage": "~25% (est.), significant retiree/fixed-income residents",
            "mobile_homes": (
                "Substantial presence of manufactured homes and older cabins. Historic mining "
                "town structures. Wood-frame construction universal. Many pre-date fire codes. "
                "Limited defensible space in forested canyon setting."
            ),
            "special_needs_facilities": (
                "None. No school (students bus to remote districts). No assisted living. No "
                "medical facilities. Community self-reliance is the only option. Some residents "
                "in 2013 refused to evacuate, complicating rescue operations."
            ),
        },
    },

    # =========================================================================
    # 6. GARDEN VALLEY, ID — New
    # =========================================================================
    "garden_valley_id": {
        "center": [44.0883, -115.9630],
        "terrain_notes": (
            "Garden Valley (pop ~380) is an unincorporated community in Boise County, situated "
            "at approximately 3,200 ft elevation along the Middle Fork of the Boise River in a "
            "narrow valley surrounded by the Boise National Forest. The community is accessed "
            "primarily via State Highway 17 (Banks-Lowman Road) from Banks on Highway 55 — a "
            "narrow, winding two-lane road through steep, forested canyon terrain. Garden Valley "
            "represents one of the most extreme WUI situations in Idaho: dispersed rural "
            "residential development deep in national forest with limited road access. The 2024 "
            "Middle Fork Complex Fire burned 61,495 acres just 9 miles east of town, triggering "
            "Level 2 evacuations along Middlefork Road. During the 2024 fire season, Garden "
            "Valley had the worst air quality in Idaho. The community relies on a volunteer fire "
            "department and has no hospital, no commercial services of scale, and limited "
            "communications infrastructure. Fires approaching from the east (Middle Fork drainage), "
            "south (along Hwy 21 from Lowman), or north (Deadwood drainage) can cut access routes "
            "and trap residents."
        ),
        "key_features": [
            {"name": "Middle Fork Boise River", "bearing": "E", "type": "drainage",
             "notes": "Major river corridor east of town. 2024 Middle Fork Complex burned along this drainage. Roads follow river — fire cuts access."},
            {"name": "Banks (Highway 55 junction)", "bearing": "W", "type": "infrastructure",
             "notes": "Junction town 15 miles west on Hwy 17. Only connection to Hwy 55 and route to Boise. Narrow canyon between Garden Valley and Banks."},
            {"name": "Deadwood Ridge", "bearing": "N", "type": "terrain",
             "notes": "Forested ridge north of community. Fire here would push south into residential areas with drainage winds."},
            {"name": "Crouch", "bearing": "SW", "type": "community",
             "notes": "Small community 5 miles west on Middlefork Road. Shares Garden Valley's vulnerability and access constraints."},
            {"name": "Terrace Lakes Resort", "bearing": "NE", "type": "development",
             "notes": "Golf resort and residential development in forest setting. Concentrated structures in high-fire-risk terrain."},
            {"name": "Lowman Road (Hwy 17/21)", "bearing": "E", "type": "corridor",
             "notes": "Road east toward Lowman. Follows river through fire-prone canyon. Access to Middle Fork backcountry."},
        ],
        "elevation_range_ft": [3100, 7200],
        "wui_exposure": "extreme",
        "historical_fires": [
            {"name": "Middle Fork Complex", "year": 2024, "acres": 61495,
             "details": "Three fires merged 9 miles east of Garden Valley. Level 2 evacuations on Middlefork Road. Garden Valley had worst air quality in Idaho. 95% contained by Oct 31."},
            {"name": "Rabbit Creek Fire", "year": 2022, "acres": 8500,
             "details": "Burned in Boise NF near Garden Valley area. Part of ongoing pattern of fires threatening community."},
            {"name": "Payette Complex", "year": 2018, "acres": 38000,
             "details": "Multiple fires in Boise NF affecting Garden Valley zone. Smoke and evacuation readiness."},
        ],
        "evacuation_routes": [
            {"route": "Highway 17 West to Banks", "direction": "W to Hwy 55", "lanes": 2,
             "bottleneck": "15-mile narrow, winding canyon road. Single paved route out. No alternate routes.",
             "risk": "Fire in canyon between Garden Valley and Banks traps the entire community. Road subject to slides and closures."},
            {"route": "Middlefork Road East", "direction": "E toward Lowman/Hwy 21", "lanes": 2,
             "bottleneck": "Rough road through fire-prone canyon along Middle Fork. Subject to fire closure (2024).",
             "risk": "2024 Middle Fork Complex closed this route. Leads through, not away from, fire terrain."},
            {"route": "Deadwood Road North", "direction": "N toward Deadwood Reservoir", "lanes": 1,
             "bottleneck": "Unpaved, remote, seasonal. Dead-ends at reservoir in wilderness.",
             "risk": "Not a viable evacuation route. Leads deeper into unroaded forest."},
        ],
        "fire_spread_characteristics": {
            "primary_wind_regime": (
                "Canyon/valley winds dominate. Afternoon up-canyon (easterly) thermal winds draw "
                "fire from surrounding forest toward the community. Nighttime drainage winds reverse "
                "but can push fire down from higher elevations. Thunderstorm outflows from afternoon "
                "convection produce erratic gusts in complex terrain."
            ),
            "critical_corridors": [
                "Middle Fork Boise River drainage — fire runs along river corridor, cuts road access",
                "Highway 17 canyon to Banks — fire here isolates entire community",
                "Deadwood drainage — north-side approach with downslope wind-driven fire",
                "South Fork tributaries — fire approaches from Lowman/Pioneer Fire area",
            ],
            "rate_of_spread_potential": (
                "Dense mixed conifer forest with significant understory fuels. Surface fire 1-2 mph, "
                "crown fire 2-4 mph in continuous canopy. Canyon terrain amplifies fire behavior with "
                "chimney effect in narrow drainages. 2024 Middle Fork Complex demonstrated multi-fire "
                "merger and rapid growth in this terrain."
            ),
            "spotting_distance": (
                "1-3 miles typical in forested terrain. Canyon updrafts can loft embers significant "
                "distances. Receptive fuels (dry forest duff, needle cast on roofs) everywhere."
            ),
        },
        "infrastructure_vulnerabilities": {
            "water_system": (
                "No municipal water system. All properties on individual wells or small community "
                "systems. No fire hydrants. Firefighting water must be drafted from rivers/ponds "
                "or trucked in. Severe constraint on structure protection."
            ),
            "power": (
                "Idaho Power distribution through forested terrain on overhead lines. Extended "
                "outages during fire events. No backup generation for community. Power loss means "
                "well pumps fail — no water for firefighting or domestic use."
            ),
            "communications": (
                "Limited cellular coverage — significant dead zones in canyon terrain. Landline "
                "service spotty. Boise County CodeRED emergency alerts. Community relies heavily "
                "on word-of-mouth and volunteer fire department notification."
            ),
            "medical": (
                "No hospital or clinic. Garden Valley has a volunteer fire/EMS department. Nearest "
                "hospital is in Boise (50+ miles, 1.5 hours via narrow Hwy 17/55). Air ambulance "
                "is weather-dependent and requires clear landing zone."
            ),
        },
        "demographics_risk_factors": {
            "population": 380,
            "seasonal_variation": (
                "Year-round pop ~380. Summer recreation season doubles or triples occupancy with "
                "vacation homes, camping, and resort visitors. Many structures are seasonal cabins "
                "with deferred maintenance and poor defensible space."
            ),
            "elderly_percentage": "~25% (65+), significant retiree population in rural setting",
            "mobile_homes": (
                "Moderate presence of manufactured homes and older cabins. Many structures built "
                "before modern fire codes, with wood shake roofs and combustible siding."
            ),
            "special_needs_facilities": (
                "Garden Valley School (K-8, ~100 students). No assisted living or medical "
                "facilities. Isolated elderly residents particularly vulnerable. Community "
                "self-reliance is both strength and limitation."
            ),
        },
    },

    # =========================================================================
    # 4. HAILEY, ID — New
    # =========================================================================
    "hailey_id": {
        "center": [43.5196, -114.3153],
        "terrain_notes": (
            "Hailey (pop ~9,200) is the largest community and economic hub of the Wood River "
            "Valley, situated at 5,322 ft elevation on the Big Wood River. The valley floor is "
            "roughly 1 mile wide at Hailey, bounded by Croy Canyon and Della Mountain (7,500 ft) "
            "to the west and the Pioneer Mountains foothills to the east. Friedman Memorial Airport "
            "(SUN) sits on the valley floor just south of town, providing the only commercial air "
            "service to the Sun Valley resort area. The 2013 Beaver Creek Fire burned directly to "
            "Hailey's western edge, with the fire entering the valley through Greenhorn Gulch and "
            "Deer Creek Canyon between Hailey and Ketchum. Complete evacuations of subdivisions on "
            "both sides of Highway 75 were ordered Aug 15-24, 2013. Hailey serves as the workforce "
            "housing center for Ketchum/Sun Valley, with a younger, more diverse population but "
            "also more manufactured housing. The town is the bottleneck for southbound evacuation "
            "from the entire upper Wood River Valley."
        ),
        "key_features": [
            {"name": "Friedman Memorial Airport (SUN)", "bearing": "S", "type": "infrastructure",
             "notes": "Regional airport at 5,318 ft. Commercial flights to SLC, Seattle, seasonal to LAX/DEN/SFO. On valley floor — vulnerable to smoke closure."},
            {"name": "Croy Canyon", "bearing": "W", "type": "drainage",
             "notes": "Major drainage west of town. Residential development extends into canyon mouth. Fire approach vector from Smoky Mountains."},
            {"name": "Deer Creek Canyon", "bearing": "NW", "type": "drainage",
             "notes": "Canyon between Hailey and Ketchum. 2013 Beaver Creek Fire entered valley through this drainage. Direct threat to subdivisions."},
            {"name": "Della Mountain", "bearing": "W", "type": "terrain",
             "notes": "7,500 ft peak immediately west of town. Steep sagebrush slopes above residential areas."},
            {"name": "Big Wood River", "bearing": "N-S", "type": "water",
             "notes": "River bisects valley through town center. Narrow riparian corridor, limited firebreak value."},
            {"name": "Quigley Canyon", "bearing": "E", "type": "drainage",
             "notes": "East-side drainage with dispersed residential development. Cross-country ski area and recreation."},
        ],
        "elevation_range_ft": [5280, 7500],
        "wui_exposure": "high",
        "historical_fires": [
            {"name": "Beaver Creek Fire", "year": 2013, "acres": 114900,
             "details": "Fire entered Wood River Valley through drainages west of Hailey. 2,300 homes evacuated between Hailey and Ketchum. Subdivisions on both sides of Hwy 75 evacuated Aug 15-24. St. Luke's Wood River evacuated."},
            {"name": "Castle Rock Fire", "year": 2007, "acres": 48000,
             "details": "Burned east side of Wood River Valley. Smoke severely impacted Hailey. Demonstrated vulnerability from multiple approach directions."},
        ],
        "evacuation_routes": [
            {"route": "Highway 75 South", "direction": "S toward Bellevue/Shoshone", "lanes": 2,
             "bottleneck": "Two-lane highway; funnels all upper Wood River Valley traffic (Ketchum, Sun Valley, Hailey) through single corridor.",
             "risk": "Total upper valley population of 15,000-25,000+ in summer must evacuate south through Hailey on one road."},
            {"route": "Highway 75 North", "direction": "N toward Ketchum", "lanes": 2,
             "bottleneck": "Leads deeper into valley. Only useful if fire is south of town.",
             "risk": "Fire between Hailey and Ketchum (as in 2013) can trap both communities."},
            {"route": "Croy Canyon Road", "direction": "W", "lanes": 2,
             "bottleneck": "Unpaved, dead-ends in forest. Not a viable evacuation route.",
             "risk": "Leads toward fire source terrain."},
        ],
        "fire_spread_characteristics": {
            "primary_wind_regime": (
                "Same valley-channeled winds as Ketchum — southerly up-valley in afternoon, "
                "northerly drainage at night. Hailey's slightly wider valley floor provides "
                "marginally more defensible space than Ketchum. However, SW frontal winds push "
                "fire from Smoky Mountains directly toward town across open sagebrush."
            ),
            "critical_corridors": [
                "Deer Creek Canyon — 2013 fire entry point between Hailey and Ketchum",
                "Croy Canyon — west-side drainage opening directly into residential areas",
                "Highway 75 corridor — continuous fuel path connecting communities",
                "Della Mountain west slopes — sagebrush/grass fire can run downslope into town",
            ],
            "rate_of_spread_potential": (
                "Sagebrush-dominated hillsides west and east of town support 2-4 mph fire spread. "
                "The 2013 Beaver Creek Fire's Aug 16 explosive run demonstrated that multiple canyons "
                "can simultaneously channel fire into the valley, overwhelming suppression resources."
            ),
            "spotting_distance": (
                "1-2 miles typical in sage/brush. Gusty conditions during 2013 fire carried embers "
                "across Highway 75 and into subdivisions on both sides of the road."
            ),
        },
        "infrastructure_vulnerabilities": {
            "water_system": (
                "Municipal water system serves town core. Outlying areas and canyon developments on "
                "wells. Fire flow capacity adequate for normal operations but stressed during "
                "simultaneous multi-structure protection."
            ),
            "power": (
                "Idaho Power distribution through valley. Overhead lines along Highway 75 corridor "
                "and into canyons. Smoke can cause flashovers on transmission lines. Extended outages "
                "during fire events."
            ),
            "communications": (
                "Good cellular coverage in town. Blaine County CodeRED emergency notification. Some "
                "canyon areas have reception gaps. Local radio station KECH provides fire updates."
            ),
            "medical": (
                "St. Luke's clinic in Hailey. Main hospital is St. Luke's Wood River in Ketchum "
                "(12 miles north) — which was itself evacuated in 2013. Nearest major trauma "
                "center is Boise (150 miles). Community health center serves Latino workforce population."
            ),
        },
        "demographics_risk_factors": {
            "population": 9200,
            "seasonal_variation": (
                "Year-round pop ~9,200, largest town in Wood River Valley. Summer and ski season "
                "add 3,000-5,000 seasonal residents/visitors. Hailey is workforce housing center — "
                "lower income than Ketchum/Sun Valley."
            ),
            "elderly_percentage": "~12% (65+), younger than Ketchum due to workforce demographics",
            "mobile_homes": (
                "More manufactured/mobile homes than Ketchum, particularly in south Hailey and "
                "Bellevue area. Higher vulnerability structures in workforce housing areas."
            ),
            "special_needs_facilities": (
                "Wood River High School (~800 students). Blaine County School District offices. "
                "Community health center. Hailey is ~30% Hispanic/Latino — language barriers in "
                "emergency communications are a documented concern."
            ),
        },
    },

    # =========================================================================
    # 3. KETCHUM / SUN VALLEY, ID — New
    # =========================================================================
    "ketchum_sun_valley_id": {
        "center": [43.6807, -114.3637],
        "terrain_notes": (
            "Ketchum (pop ~3,550) and Sun Valley (pop ~1,780) occupy a narrow section of the "
            "Wood River Valley at 5,850-5,920 ft elevation, hemmed in by the Boulder Mountains to "
            "the north and the Smoky Mountains to the west. The Sawtooth National Forest surrounds "
            "the communities on all sides. The valley floor is only 0.5-1 mile wide in places, with "
            "steep sagebrush and conifer-covered slopes rising 3,000-4,000 ft above town. Baldy "
            "Mountain (Sun Valley ski area) rises directly to the east. Multiple side canyons — "
            "Warm Springs, Cold Springs, Trail Creek, Greenhorn Gulch, Deer Creek — open onto the "
            "valley floor and can channel fire directly into town. The 2013 Beaver Creek Fire "
            "(114,900 acres) entered the valley through Greenhorn Gulch and Deer Creek Canyon, "
            "forcing evacuation of 2,300 homes. In 2024, the Wapiti Fire (126,817 acres) and 38 "
            "other fire starts on the Sawtooth NF smothered the valley in smoke. This is a wealthy "
            "resort community with seasonal population swings of 3-5x, a regional airport, and "
            "a hospital — but only one highway (Hwy 75) threading the narrow valley for egress."
        ),
        "key_features": [
            {"name": "Bald Mountain (Baldy)", "bearing": "E", "type": "terrain",
             "notes": "Sun Valley ski area, summit 9,150 ft. Steep east-facing slopes above town. Mixed conifer and sage."},
            {"name": "Greenhorn Gulch", "bearing": "W", "type": "drainage",
             "notes": "Canyon midway between Hailey and Ketchum. Entry point for 2013 Beaver Creek Fire into the valley. Direct threat corridor."},
            {"name": "Trail Creek Canyon", "bearing": "E", "type": "corridor",
             "notes": "Drainage east of Ketchum leading to Trail Creek summit. Funnels east winds and fire toward town."},
            {"name": "Warm Springs Canyon", "bearing": "W", "type": "drainage",
             "notes": "Major drainage west of Ketchum feeding Warm Springs residential area and ski base. Fire channel from Smoky Mtns."},
            {"name": "Big Wood River", "bearing": "N-S", "type": "water",
             "notes": "Flows south through valley floor. Minimal firebreak value due to narrow riparian zone."},
            {"name": "Sawtooth NRA", "bearing": "N", "type": "wilderness",
             "notes": "National Recreation Area begins just north of town. Unmanaged fuels in wilderness provide unlimited fire source."},
        ],
        "elevation_range_ft": [5750, 9150],
        "wui_exposure": "extreme",
        "historical_fires": [
            {"name": "Beaver Creek Fire", "year": 2013, "acres": 114900,
             "details": "Lightning-caused Aug 7. Exploded Aug 16 driven by erratic south/west winds. Entered Wood River Valley through Greenhorn Gulch. 2,300 homes evacuated between Hailey and Ketchum. St. Luke's Wood River evacuated patients. One of Idaho's worst-ever wildfires."},
            {"name": "Castle Rock Fire", "year": 2007, "acres": 48000,
             "details": "Burned on the east side of the Wood River Valley. Threatened Ketchum and Sun Valley. Significant smoke impacts on resort communities."},
            {"name": "Wapiti Fire (smoke impact)", "year": 2024, "acres": 126817,
             "details": "Lightning-caused near Grandjean. While not directly threatening Ketchum, smoke smothered the valley for weeks. 38 total fire starts on Sawtooth NF in 2024 season."},
        ],
        "evacuation_routes": [
            {"route": "Highway 75 South", "direction": "S toward Hailey/Shoshone", "lanes": 2,
             "bottleneck": "Only paved route south. Passes through Hailey — if fire crosses Hwy 75 between towns (as nearly happened in 2013), both communities trapped.",
             "risk": "2013 Beaver Creek Fire crossed terrain adjacent to Hwy 75. Smoke can reduce visibility to zero."},
            {"route": "Highway 75 North", "direction": "N toward Stanley/Sawtooth", "lanes": 2,
             "bottleneck": "Galena Summit (8,701 ft) — steep, narrow, winter-closure road. 60 miles to Stanley with no services.",
             "risk": "Not viable for mass evacuation. Road crosses high-elevation terrain impassable in bad weather."},
            {"route": "Trail Creek Road", "direction": "E toward Mackay", "lanes": 2,
             "bottleneck": "Unpaved/gravel sections over Trail Creek Summit (7,760 ft). Steep, narrow, seasonal.",
             "risk": "Emergency-only alternate. Cannot handle significant traffic volume."},
        ],
        "fire_spread_characteristics": {
            "primary_wind_regime": (
                "Valley channeling dominates — afternoon up-valley (southerly) winds 10-20 mph, "
                "nighttime down-valley (northerly) drainage. Strong SW winds during frontal passages "
                "push fire out of Smoky Mountains directly into the valley (as in 2013 Beaver Creek). "
                "The narrow valley acts as a chimney, accelerating wind flow through the constriction "
                "between Baldy and the Smoky Range."
            ),
            "critical_corridors": [
                "Greenhorn Gulch — 2013 Beaver Creek entry point; direct path Smoky Mtns to Hwy 75",
                "Deer Creek Canyon — secondary 2013 entry point, south of Greenhorn",
                "Warm Springs drainage — channels fire from west directly into Ketchum",
                "Trail Creek Canyon — east-side threat corridor funneling wind and fire into town",
                "Big Wood River corridor — continuous valley-floor fuel path connecting communities",
            ],
            "rate_of_spread_potential": (
                "Sagebrush/grass slopes support 2-4 mph spread; conifer forests 1-3 mph surface, "
                "3-5 mph in crown fire. The 2013 Beaver Creek Fire demonstrated explosive runs on "
                "Aug 16 when winds shifted — multiple drainages simultaneously channeled fire into "
                "the valley floor at rates exceeding any defensible response window."
            ),
            "spotting_distance": (
                "1-3 miles in typical conditions. Canyon terrain amplifies convective lift, increasing "
                "spotting potential. Ember showers from Greenhorn Gulch fire run in 2013 landed in "
                "subdivisions on both sides of Highway 75."
            ),
        },
        "infrastructure_vulnerabilities": {
            "water_system": (
                "Municipal systems in Ketchum and Sun Valley adequate for normal operations. Fire "
                "flow capacity stressed during large-scale structure protection. Many rural-residential "
                "properties in canyons on private wells with no hydrant access."
            ),
            "power": (
                "Idaho Power transmission through forested mountain corridors. Long lead times for "
                "repair in remote terrain. Overhead lines in canyon drainages are vulnerable. "
                "Extended outages during fire events impact water pumping."
            ),
            "communications": (
                "Good cellular and fiber coverage in town centers. Canyon areas and mountain slopes "
                "have significant coverage gaps. Blaine County Sheriff CodeRED alerts. Radio repeaters "
                "on mountain peaks vulnerable to fire damage."
            ),
            "medical": (
                "St. Luke's Wood River Medical Center in Ketchum — 25-bed facility with 24-hour ER. "
                "Was evacuated during 2013 Beaver Creek Fire. Nearest major trauma center is Boise "
                "(150 miles, 2.5 hours). Limited mass casualty capacity."
            ),
        },
        "demographics_risk_factors": {
            "population": 5330,
            "seasonal_variation": (
                "Combined year-round pop ~5,330 (Ketchum + Sun Valley). Swells to 15,000-25,000 "
                "during ski season (Dec-Apr) and summer season (Jun-Sep). Wealthy second-home "
                "community — many properties unoccupied and undefended during fire events. Summer "
                "visitors unfamiliar with evacuation routes."
            ),
            "elderly_percentage": "~20% (65+), significant retiree/second-home demographic",
            "mobile_homes": (
                "Very few in Ketchum/Sun Valley proper due to high property values. Workforce "
                "housing in Hailey and Bellevue includes some manufactured homes."
            ),
            "special_needs_facilities": (
                "St. Luke's Wood River hospital (required evacuation in 2013). Multiple luxury "
                "lodges and hotels housing transient visitors. Sun Valley Resort can host 2,000+ "
                "guests who may need coordinated evacuation. Community School of Sun Valley."
            ),
        },
    },

    # =========================================================================
    # 9. LOWMAN, ID — New
    # =========================================================================
    "lowman_id": {
        "center": [44.0833, -115.6167],
        "terrain_notes": (
            "Lowman (pop ~44) is an unincorporated community in Boise County at 3,960 ft "
            "elevation, nestled along the South Fork of the Payette River in the heart of "
            "the Boise National Forest. Highway 21 (Ponderosa Pine Scenic Byway) is the sole "
            "paved road, connecting Lowman to Boise (75 miles southwest) and Stanley (65 miles "
            "northeast). Lowman has been devastated by wildfire repeatedly: the 1989 Lowman Fire "
            "burned 45,000 acres (72 sq miles) and destroyed 26 structures in the community; "
            "the 2016 Pioneer Fire (189,032 acres) crossed Highway 21 at Lowman with 40 mph "
            "gusts, triggering Level 2 evacuations; and the 2024 Bulltrout Fire burned 35 miles "
            "northeast. A historical marker in Lowman states: 'During the last 100 years, the "
            "natural fire cycle has been altered by humans putting out fires, and as a result, "
            "unnaturally abundant fuels built up in the Lowman area.' The community sits in a "
            "narrow river canyon with forested slopes rising steeply on all sides — there is "
            "essentially no defensible space at the landscape level."
        ),
        "key_features": [
            {"name": "South Fork Payette River", "bearing": "E-W", "type": "water",
             "notes": "River flows through Lowman. Narrow canyon with Highway 21 on the bank. Fire terrain on both sides of river."},
            {"name": "Highway 21 (Ponderosa Pine Scenic Byway)", "bearing": "SW-NE", "type": "corridor",
             "notes": "Only paved road. Connects Boise to Stanley through Boise NF. Routinely closed by fire — 50+ miles closed in 2024."},
            {"name": "Pioneer Fire burn scar (2016)", "bearing": "S", "type": "terrain",
             "notes": "189,000-acre burn scar south/east of Lowman. Reburned areas have dense brush regrowth. Dead standing timber remains."},
            {"name": "Kirkham Hot Springs", "bearing": "W", "type": "recreation",
             "notes": "Popular hot springs 4 miles west. Concentrates recreators in fire-prone canyon terrain."},
            {"name": "Grandjean (Hwy 21)", "bearing": "NE", "type": "trailhead",
             "notes": "Backcountry access point 25 miles NE. Origin area of 2024 Wapiti Fire. Highway 21 closure cut Stanley access."},
            {"name": "Lowman Ranger District", "bearing": "local", "type": "infrastructure",
             "notes": "USFS ranger station. Provides some fire suppression resources. One of few institutional structures in community."},
        ],
        "elevation_range_ft": [3960, 8200],
        "wui_exposure": "extreme",
        "historical_fires": [
            {"name": "Lowman Fire", "year": 1989, "acres": 45000,
             "details": "Burned 72 sq miles from July 26 to Aug 30. Destroyed 26 structures in community. No injuries or fatalities. Altered by unnaturally abundant fuel buildup from fire suppression."},
            {"name": "Pioneer Fire", "year": 2016, "acres": 189032,
             "details": "Massive fire in Boise NF. Crossed Highway 21 at Lowman with 20 mph sustained winds, 28-40 mph gusts. Level 2 evacuations. 900 acres aerial mulching, 300 miles road drainage reconstruction in BAER response."},
            {"name": "Bulltrout Fire", "year": 2024, "acres": 5000,
             "details": "Lightning-caused July 24, 35 miles NE of Lowman. Part of the extreme 2024 central Idaho fire season."},
            {"name": "Wapiti Fire (Hwy 21 closure)", "year": 2024, "acres": 126817,
             "details": "While centered near Grandjean, the Wapiti Fire closed Highway 21 from Lowman to Stanley — cutting Lowman's only route northeast."},
        ],
        "evacuation_routes": [
            {"route": "Highway 21 Southwest", "direction": "SW toward Idaho City/Boise (75 mi)", "lanes": 2,
             "bottleneck": "Narrow, winding mountain highway through Boise NF. 75 miles to Boise. Passes through 2016 Pioneer Fire burn scar.",
             "risk": "Fire or slides close this road frequently. Only paved route to civilization. No services for 35+ miles to Idaho City."},
            {"route": "Highway 21 Northeast", "direction": "NE toward Stanley (65 mi)", "lanes": 2,
             "bottleneck": "Crosses Banner Summit (7,056 ft). 2024 Wapiti Fire closed 50 miles of this route.",
             "risk": "Routinely closed by fire, avalanche, winter weather. Leads toward more remote terrain, not toward services."},
            {"route": "South Fork Payette Road", "direction": "E toward Garden Valley (30 mi)", "lanes": 1,
             "bottleneck": "Rough, unpaved road along river. Subject to fire closure and flooding.",
             "risk": "Not a reliable evacuation route. Connects to Garden Valley which has its own access constraints."},
        ],
        "fire_spread_characteristics": {
            "primary_wind_regime": (
                "Canyon wind regime dominates. Strong afternoon up-canyon thermal winds from the "
                "southwest, nighttime drainage from northeast. The 2016 Pioneer Fire demonstrated "
                "the danger: sustained 20 mph south winds with 28-40 mph gusts pushed fire across "
                "Highway 21 and directly through the community. Canyon constriction at Lowman "
                "accelerates wind flow."
            ),
            "critical_corridors": [
                "South Fork Payette River canyon — fire channeled along Highway 21 corridor directly through community",
                "Highway 21 NE toward Grandjean — 2024 Wapiti Fire approach",
                "Side drainages from south (Pioneer Fire area) — downslope fire approach",
                "Deadwood River drainage from north — fire approach from NE direction",
            ],
            "rate_of_spread_potential": (
                "Dense conifer forest in narrow canyon. Surface fire 1-2 mph. Crown fire in "
                "continuous canopy 2-4 mph. Canyon chimney effect can produce extreme rates during "
                "wind events — the 2016 Pioneer Fire's crossing of Hwy 21 at 40 mph gusts "
                "demonstrates potential for overwhelming any defensive measures. Post-fire brush "
                "regrowth in 1989 and 2016 burn scars adds flashy fuels."
            ),
            "spotting_distance": (
                "1-2 miles in typical conditions. Canyon updrafts amplify spotting. The narrow "
                "canyon at Lowman means any significant spotting crosses the entire community. "
                "Receptive fuels on roofs, in yards, and forest duff everywhere."
            ),
        },
        "infrastructure_vulnerabilities": {
            "water_system": (
                "No municipal water system. Individual wells. No fire hydrants. South Fork Payette "
                "River provides drafting source but requires equipment. 26 structures lost in 1989 "
                "partly due to inability to mount effective water-based defense."
            ),
            "power": (
                "Idaho Power single feed through forested canyon. Power poles in fire corridor. "
                "Extended outages during any nearby fire. No backup generation. Power loss = no "
                "well pumps = no water."
            ),
            "communications": (
                "Minimal cellular coverage. Deep canyon blocks signals. USFS ranger station has "
                "radio. Satellite communication limited. Landline service unreliable. Community "
                "notification is essentially door-to-door in a community of 44 people."
            ),
            "medical": (
                "No medical facilities whatsoever. Nearest clinic is Idaho City (35 miles). "
                "Nearest hospital is Boise (75 miles, 1.5-2 hours on winding mountain road). "
                "Medical emergency during active fire = potentially fatal delay."
            ),
        },
        "demographics_risk_factors": {
            "population": 44,
            "seasonal_variation": (
                "Year-round pop ~44 (2020 Census). Summer recreation at hot springs, river "
                "activities, and campgrounds increases effective population 5-10x. Kirkham Hot "
                "Springs alone can have 200+ visitors on summer weekends. Many campers dispersed "
                "in forest along Highway 21 corridor."
            ),
            "elderly_percentage": "~30% (est.), small population skews older",
            "mobile_homes": (
                "Mix of manufactured homes, older cabins, and a few newer structures. Most "
                "buildings pre-date fire codes. Wood-frame construction universal. Limited "
                "defensible space due to canyon terrain and forest encroachment."
            ),
            "special_needs_facilities": (
                "None. No school (students bus to Idaho City or Garden Valley). No assisted "
                "living. Community is essentially self-reliant. Volunteer fire department provides "
                "first response. Mutual aid response times measured in hours, not minutes."
            ),
        },
    },

    # =========================================================================
    # 2. McCALL, ID — Enhanced (Payette NF, mountain resort)
    # =========================================================================
    "mccall_id": {
        "center": [44.9108, -116.0987],
        "terrain_notes": (
            "McCall (pop ~3,700) sits on the southern shore of Payette Lake at 5,021 ft elevation, "
            "surrounded on three sides by the Payette National Forest. The town occupies a narrow "
            "bench between the lake and forested mountains that rise to 8,000-9,000 ft within a few "
            "miles. Dense lodgepole pine, Douglas-fir, and subalpine fir forests extend from the "
            "town boundary to the Selway-Bitterroot and Frank Church-River of No Return wilderness "
            "areas. The 2007 Cascade Complex fires burned over 300,000 acres in the Boise and "
            "Payette NFs with extreme fire behavior including 300-ft flame lengths, crown runs, "
            "and confirmed spotting distances of 5-7 miles (unconfirmed to 15 miles). McCall hosts "
            "a USFS Smokejumper Base on its municipal airport, making it a critical node in "
            "national fire response. The Southwest Idaho Wildfire Crisis Landscape Project "
            "identifies McCall as one of 14 community cores with elevated transboundary fire "
            "exposure risk. Population triples in summer with tourists and vacation homeowners. "
            "Highway 55 is the sole paved route south — a two-lane road through the Payette "
            "River canyon that is routinely threatened by fire and rock slides."
        ),
        "key_features": [
            {"name": "Payette Lake", "bearing": "N", "type": "water",
             "notes": "Glacier-carved, 4,987-acre lake (8.3 sq mi), max depth 304 ft. Northern shore is unroaded NF land. Provides natural firebreak on town's north side."},
            {"name": "McCall Smokejumper Base", "bearing": "S", "type": "infrastructure",
             "notes": "USFS smokejumper facility on McCall Airport. Critical national asset; one of few remaining active smokejumper bases."},
            {"name": "Brundage Mountain", "bearing": "NW", "type": "terrain",
             "notes": "Ski area 8 miles NW of town. Mixed conifer forest on steep terrain; fire in this drainage would threaten Warren Wagon Road corridor."},
            {"name": "Lick Creek Range", "bearing": "E", "type": "terrain",
             "notes": "8,000-9,000 ft range east of town. Dense forest with significant beetle-kill standing dead timber. Fire here would threaten east McCall."},
            {"name": "Warren Wagon Road", "bearing": "N", "type": "corridor",
             "notes": "Unpaved historic road north into remote backcountry. Only access to Warren and several trailheads. Single-track, no turnarounds."},
            {"name": "North Fork Payette River", "bearing": "S", "type": "drainage",
             "notes": "River corridor south toward Cascade. Highway 55 follows this canyon — fire or slides close the only paved route out."},
        ],
        "elevation_range_ft": [5021, 9100],
        "wui_exposure": "extreme",
        "historical_fires": [
            {"name": "Cascade Complex", "year": 2007, "acres": 300000,
             "details": "Multiple fires merged in central Idaho. Extreme behavior on Aug 13 — 300-ft flame lengths, crown runs, confirmed 5-7 mile spotting. Burned in Payette and Boise NFs surrounding McCall region."},
            {"name": "Burgdorf Junction Fire", "year": 2003, "acres": 24000,
             "details": "Burned north of McCall in Payette NF. Threatened Warren Road corridor and remote communities."},
            {"name": "Rock Fire", "year": 2025, "acres": 2844,
             "details": "Lightning-caused fire near Tamarack Resort (20 mi S of McCall). Forced resort closure, Level 2 evacuations for west Lake Cascade residents. ~700 personnel deployed."},
        ],
        "evacuation_routes": [
            {"route": "Highway 55 South", "direction": "S toward Cascade/Boise", "lanes": 2,
             "bottleneck": "Payette River canyon — narrow, winding, single route south. 70+ miles to Boise through fire-prone terrain.",
             "risk": "Routinely threatened by wildfire. Rock slides and winter closures. No alternate paved route."},
            {"route": "Highway 55 North to New Meadows", "direction": "N toward US-95", "lanes": 2,
             "bottleneck": "30 miles to New Meadows junction. US-95 provides north-south alternative but adds 100+ miles.",
             "risk": "Forest-lined highway with fire exposure. Limited passing opportunities."},
            {"route": "Warren Wagon Road", "direction": "NE into backcountry", "lanes": 1,
             "bottleneck": "Unpaved, single-lane, no services. Dead-ends in remote Warren mining district.",
             "risk": "Not a viable evacuation route — leads deeper into fire-prone wilderness."},
        ],
        "fire_spread_characteristics": {
            "primary_wind_regime": (
                "Afternoon SW thermal winds 10-20 mph channeled by Payette River valley. Nighttime "
                "drainage winds from surrounding peaks. Thunderstorm outflows from July-August convection "
                "can produce erratic 40-60 mph gusts with dry lightning, as seen in the 2007 Cascade "
                "Complex when inversion breakup unleashed extreme fire behavior."
            ),
            "critical_corridors": [
                "Payette River canyon south — fire here cuts sole highway to Boise",
                "Lick Creek drainage east — dense forest funnels fire toward east McCall",
                "Lake Fork drainage — connects wildland fire to residential development",
                "Brundage Mountain NW slopes — steep terrain above Warren Wagon Road",
            ],
            "rate_of_spread_potential": (
                "Mixed conifer forests support 1-3 mph surface fire spread under moderate conditions. "
                "Crown fire in continuous canopy can achieve 3-5 mph. The 2007 Cascade Complex "
                "demonstrated that post-inversion breakup conditions produce very rapid crown runs "
                "with extreme spotting. Beetle-kill standing dead increases torching potential."
            ),
            "spotting_distance": (
                "5-7 miles confirmed during 2007 Cascade Complex, with unconfirmed reports of 15 miles. "
                "Terrain-amplified convective columns in mountain valleys can loft embers to extreme "
                "distances. McCall's forested neighborhoods are highly receptive to long-range spotting."
            ),
        },
        "infrastructure_vulnerabilities": {
            "water_system": (
                "Municipal system draws from Payette Lake — abundant supply. However, distribution "
                "mains are limited in newer developments outside city limits. Rural properties on "
                "individual wells with no fire hydrant access."
            ),
            "power": (
                "Idaho Power transmission through forested corridors. Lines vulnerable to tree fall "
                "and fire damage. Extended outages during major fire events common in surrounding area. "
                "Hospital and smokejumper base have backup generation."
            ),
            "communications": (
                "Cellular coverage good in town, poor in surrounding wilderness. Radio repeaters on "
                "mountain peaks can be damaged by fire. Satellite communication backup for USFS "
                "operations. Emergency alert system via Valley County Sheriff."
            ),
            "medical": (
                "St. Luke's McCall — 15-bed community hospital expanded to 65,000 sq ft in 2023. "
                "Limited capacity for mass casualty. Nearest Level II trauma is Boise (100+ miles, "
                "2+ hours by ground). Helicopter medevac available weather permitting."
            ),
        },
        "demographics_risk_factors": {
            "population": 3700,
            "seasonal_variation": (
                "Year-round pop ~3,700 triples to 10,000-12,000 in summer with tourists, vacation "
                "homeowners, and seasonal workers. Winter ski season adds another population surge. "
                "Many visitors unfamiliar with fire evacuation procedures."
            ),
            "elderly_percentage": "~18% (65+), significant retiree community",
            "mobile_homes": (
                "Limited within city limits. Some mobile/manufactured homes in unincorporated "
                "Valley County areas south of town along Highway 55."
            ),
            "special_needs_facilities": (
                "St. Luke's McCall hospital, one assisted living facility. McCall-Donnelly School "
                "District serves ~900 students. Summer camps and outdoor education programs bring "
                "children into fire-prone backcountry."
            ),
        },
    },

    # =========================================================================
    # 8. SALMON, ID — New
    # =========================================================================
    "salmon_id": {
        "center": [45.1758, -113.8953],
        "terrain_notes": (
            "Salmon (pop ~3,300) is the county seat of Lemhi County, situated at ~3,950 ft "
            "elevation at the confluence of the Salmon River and the Lemhi River. The town is "
            "the economic and services hub for a vast, sparsely populated region — the nearest "
            "city of any size is Idaho Falls (160 miles east) or Missoula, MT (150 miles north). "
            "The Salmon River corridor runs east-west through town, flanked by steep, sagebrush "
            "and conifer-covered mountains rising 4,000+ ft above the valley floor. The 2022 "
            "Moose Fire (130,111 acres) — Idaho's largest fire that year — burned from a campfire "
            "left unattended in Lemhi County, with wind gusts to 55 mph driving extreme fire "
            "behavior and forcing evacuations of multiple zones around Salmon. Two helicopter "
            "pilots died fighting the Moose Fire. In 2024, the Elkhorn Fire made a 20,000-acre "
            "run of extreme behavior up the Salmon River, and the Red Rock Fire (78,795 acres) "
            "burned 15 miles west of town with 60+ mph winds that trapped 45 firefighters when "
            "the blaze destroyed a bridge. Highway 93 is the sole major route, running north-south "
            "through the valley."
        ),
        "key_features": [
            {"name": "Salmon River", "bearing": "E-W", "type": "water",
             "notes": "The 'River of No Return' flows through town. Corridor channels fire and wind. Steep canyon walls above town."},
            {"name": "Lemhi Range", "bearing": "E", "type": "terrain",
             "notes": "Mountain range east of Lemhi Valley. 10,000+ ft peaks. Sagebrush/grass lower slopes, conifer higher. Fire approach vector from east."},
            {"name": "Bitterroot Range", "bearing": "W", "type": "terrain",
             "notes": "Continental Divide west of Salmon. Frank Church Wilderness beyond. Unmanaged fuels in vast wilderness."},
            {"name": "North Fork (Salmon River)", "bearing": "N", "type": "community",
             "notes": "Small community 20 miles north at river junction. 2022 Moose Fire forced evacuations in this area."},
            {"name": "Panther Creek", "bearing": "W", "type": "drainage",
             "notes": "Major drainage west of Salmon. 2024 Red Rock Fire started near Panther Creek. Canyon terrain funnels fire toward town."},
            {"name": "Salmon-Challis NF", "bearing": "all directions", "type": "forest",
             "notes": "4.3 million acre national forest/wilderness complex surrounds town. Largest NF in lower 48. Vast unmanaged fuel loads."},
        ],
        "elevation_range_ft": [3900, 10985],
        "wui_exposure": "high",
        "historical_fires": [
            {"name": "Moose Fire", "year": 2022, "acres": 130111,
             "details": "Human-caused (unattended campfire). Idaho's largest fire of 2022. 55 mph wind gusts drove extreme behavior. Multiple evacuation zones activated around Salmon. Two helicopter pilots killed July 20. Burned 200+ square miles."},
            {"name": "Red Rock Fire", "year": 2024, "acres": 78795,
             "details": "Lightning-caused Sept 2 near Panther Creek, 15 miles west. 60+ mph wind gusts. Destroyed bridge, trapping 45 firefighters Oct 5. 19% contained by October."},
            {"name": "Elkhorn Fire", "year": 2024, "acres": 26048,
             "details": "Burned in Salmon River corridor. Made 20,000-acre run of extreme fire behavior. One structure lost at Yellow Pine Ranch, seven buildings at Allison Ranch."},
            {"name": "Thunder Fire", "year": 2024, "acres": 2474,
             "details": "Lightning-caused July 24, 12 miles SW of Salmon. Burned in timber, sagebrush, grass. 100% contained."},
        ],
        "evacuation_routes": [
            {"route": "US-93 North", "direction": "N toward Missoula, MT (150 mi)", "lanes": 2,
             "bottleneck": "Two-lane highway through North Fork canyon. 150 miles to Missoula. Passes through 2022 Moose Fire area.",
             "risk": "Fire in Salmon River or North Fork canyon closes sole northern route. Remote canyon with no alternate roads."},
            {"route": "US-93 South", "direction": "S toward Challis (60 mi)", "lanes": 2,
             "bottleneck": "Follows Salmon River through canyon. 60 miles to Challis, then 160 miles to Idaho Falls.",
             "risk": "Fire in Salmon River corridor cuts route. 2024 Elkhorn Fire burned along this corridor."},
            {"route": "Highway 28 East", "direction": "E toward Tendoy/Leadore", "lanes": 2,
             "bottleneck": "Follows Lemhi River valley east. Remote, no services for 60 miles.",
             "risk": "Connects to US-93 at Lost Trail Pass or Highway 28 south. Adds hours to any evacuation."},
        ],
        "fire_spread_characteristics": {
            "primary_wind_regime": (
                "Salmon River canyon creates powerful wind channeling. Up-canyon (westerly) thermal "
                "winds in afternoon, down-canyon (easterly) drainage at night. Frontal passages "
                "produce extreme wind events — the 2022 Moose Fire saw 55 mph gusts, and the 2024 "
                "Red Rock Fire experienced 60+ mph winds that destroyed infrastructure. The canyon "
                "terrain amplifies wind speeds through constriction effects."
            ),
            "critical_corridors": [
                "Salmon River corridor — fire channeled by canyon directly toward/through town",
                "Panther Creek drainage — 2024 Red Rock Fire approach from west",
                "North Fork Salmon River — 2022 Moose Fire approach from north",
                "Lemhi Valley — sagebrush-dominated, rapid fire spread east of town",
            ],
            "rate_of_spread_potential": (
                "Sagebrush/grass fuels on valley floor and lower slopes support 3-6 mph spread. "
                "Canyon terrain accelerates fire behavior dramatically — the 2024 Elkhorn Fire's "
                "20,000-acre run demonstrates the potential for extreme rates in the Salmon River "
                "corridor. Conifer forests at higher elevations support crown fire at 2-4 mph."
            ),
            "spotting_distance": (
                "1-3 miles typical. Canyon convective dynamics can produce longer spotting. The "
                "2022 Moose Fire's 55 mph winds and 2024 Red Rock Fire's 60+ mph winds demonstrate "
                "the potential for extreme ember transport in this terrain."
            ),
        },
        "infrastructure_vulnerabilities": {
            "water_system": (
                "Municipal system serves town core. Rural areas on wells. Water supply from Salmon "
                "River adequate but treatment/distribution capacity limited for large-scale "
                "firefighting. Upstream fire debris in river can impact water quality."
            ),
            "power": (
                "Idaho Power long-distance transmission through remote terrain. Single feed, no "
                "redundancy. Power poles in fire-prone corridors. Extended outages during major "
                "fire events — infrastructure destroyed (2024 Red Rock Fire destroyed bridge)."
            ),
            "communications": (
                "Cellular coverage in town, very poor in surrounding canyons and wilderness. "
                "Lemhi County emergency alerts. Radio repeaters on peaks vulnerable to fire. "
                "Satellite phones used by USFS but not available to public. Large communication "
                "dead zones on highways."
            ),
            "medical": (
                "Steele Memorial Medical Center — 25-bed critical access hospital with ER. Local "
                "VA clinic. This is the ONLY hospital for a region larger than some states. "
                "Nearest additional hospital is Challis (60 mi) or Idaho Falls (160 mi). "
                "Air ambulance weather-dependent in canyon terrain."
            ),
        },
        "demographics_risk_factors": {
            "population": 3300,
            "seasonal_variation": (
                "Year-round pop ~3,300. Summer increases 50-100% with rafters, outfitters, hunters, "
                "and tourists accessing Frank Church Wilderness and Salmon River. Fall hunting "
                "season brings additional visitors to remote backcountry. Many visitors are miles "
                "from roads in wilderness when fires start."
            ),
            "elderly_percentage": "~22% (65+), aging rural community",
            "mobile_homes": (
                "Significant manufactured/mobile home presence. Lower property values in Lemhi "
                "County. Many structures lack fire-resistant construction. Some older mobile homes "
                "in flood/fire interface zones along rivers."
            ),
            "special_needs_facilities": (
                "Steele Memorial Medical Center. Salmon River School District. County senior "
                "center. Limited assisted living. Isolated elderly and disabled residents in "
                "remote river locations particularly vulnerable."
            ),
        },
    },

    # =========================================================================
    # 7. STANLEY, ID — New
    # =========================================================================
    "stanley_id": {
        "center": [44.2075, -114.9381],
        "terrain_notes": (
            "Stanley (pop ~120) sits at 6,250 ft elevation at the confluence of Valley Creek "
            "and the Salmon River in the Sawtooth Valley — a broad, high-elevation basin ringed "
            "by the Sawtooth Range (10,000+ ft) to the west, the White Cloud Peaks to the east, "
            "and the Salmon River Mountains to the north. Stanley is often cited as the coldest "
            "town in the lower 48 states (record -54F, avg annual temp 21.2F). Despite its "
            "extreme remoteness — 130 miles from Boise, 60 miles from the nearest town of any "
            "size — Stanley is a hub for recreation in the Sawtooth National Recreation Area "
            "and Frank Church-River of No Return Wilderness. The 2024 fire season was catastrophic: "
            "the Wapiti Fire (126,817 acres) burned from Grandjean toward Stanley, closing 50 miles "
            "of Highway 21 and forcing evacuation preparation. Crews built indirect fireline from "
            "the Stanley Ranger Station to Redfish Lake. The Bench Lake Fire (2,600 acres) closed "
            "Redfish Lake Lodge. Highway 75 (south to Sun Valley) and Highway 21 (west to Boise) "
            "are the only routes, and both traverse remote fire-prone terrain."
        ),
        "key_features": [
            {"name": "Sawtooth Range", "bearing": "W", "type": "terrain",
             "notes": "Jagged granite peaks to 10,751 ft (Thompson Peak). Wilderness boundary within 5 miles. Unmanaged fuels."},
            {"name": "Redfish Lake", "bearing": "SW", "type": "water",
             "notes": "Iconic alpine lake 5 miles south. Lodge and campgrounds host thousands of visitors. 2024 Bench Lake Fire forced closure."},
            {"name": "Salmon River", "bearing": "N-E", "type": "water",
             "notes": "Headwaters of the River of No Return. Flows north through Stanley then east. River corridor is primary fire approach vector from east."},
            {"name": "Galena Summit", "bearing": "S", "type": "terrain",
             "notes": "8,701 ft pass on Hwy 75 south of Stanley. High-elevation crossing to Wood River Valley. Winter closures, avalanche zones."},
            {"name": "Highway 21 / Grandjean", "bearing": "W", "type": "corridor",
             "notes": "Route to Boise via Banner Summit (7,056 ft). 2024 Wapiti Fire closed 50 miles of this highway. Passes through Boise NF fire terrain."},
            {"name": "White Cloud Peaks", "bearing": "E", "type": "terrain",
             "notes": "11,000+ ft peaks east of Stanley. Castle Peak (11,815 ft). Wilderness area with unmanaged fuels in lower elevations."},
        ],
        "elevation_range_ft": [6100, 10751],
        "wui_exposure": "extreme",
        "historical_fires": [
            {"name": "Wapiti Fire", "year": 2024, "acres": 126817,
             "details": "Lightning-caused July 24 near Grandjean. Burned across Boise NF, Sawtooth NF, Sawtooth Wilderness, and Salmon-Challis NF. Closed Hwy 21 for 50 miles. Crews built fireline from Stanley Ranger Station to Redfish Lake. 80% contained with 186 personnel."},
            {"name": "Bench Lake Fire", "year": 2024, "acres": 2600,
             "details": "Ignited 1 mile west of Redfish Lake on July 11. Doubled in size daily for first week. Closed Redfish Lake Lodge and campgrounds — major economic/recreation impact."},
            {"name": "Valley Road Fire", "year": 2005, "acres": 12000,
             "details": "Burned in Sawtooth Valley near Stanley. Threatened homes and infrastructure in the community."},
        ],
        "evacuation_routes": [
            {"route": "Highway 75 South", "direction": "S toward Sun Valley (60 mi)", "lanes": 2,
             "bottleneck": "Galena Summit (8,701 ft) — steep, narrow, winter-closure road. 60 miles to Ketchum with no services.",
             "risk": "High-elevation pass impassable in winter. Fire or avalanche can close. No alternate route."},
            {"route": "Highway 21 West", "direction": "W toward Boise (130 mi)", "lanes": 2,
             "bottleneck": "Banner Summit (7,056 ft), then drops through Lowman/Idaho City. 50 miles closed by 2024 Wapiti Fire.",
             "risk": "Passes through extreme fire terrain in Boise NF. Routinely closed by wildfire, slides, winter weather."},
            {"route": "Highway 75 North to Challis", "direction": "N/E toward Challis (60 mi)", "lanes": 2,
             "bottleneck": "Follows Salmon River through remote canyon. No services for 60 miles.",
             "risk": "Fire in Salmon River corridor can close this route. Extremely remote — no cell service for much of distance."},
        ],
        "fire_spread_characteristics": {
            "primary_wind_regime": (
                "Sawtooth Valley is a high-elevation basin with complex wind patterns. Afternoon "
                "thermal winds draw up-valley (southerly) through the valley floor. Strong nocturnal "
                "drainage from surrounding peaks (10,000+ ft) creates cold-pool inversions that "
                "suppress overnight fire but trap smoke. Frontal passages and thunderstorm outflows "
                "produce the most dangerous conditions — sudden wind shifts with 40-60 mph gusts "
                "that break inversions and unleash explosive fire behavior."
            ),
            "critical_corridors": [
                "Salmon River corridor east — primary fire approach vector; 2024 fires burned along this axis",
                "Highway 21 / Grandjean drainage west — 2024 Wapiti Fire approach",
                "Redfish Lake / Alturas Lake drainages south — fire approaches from Sawtooth Wilderness",
                "Valley Creek drainage — connects fire from NE directly to Stanley",
            ],
            "rate_of_spread_potential": (
                "Mixed lodgepole pine and Douglas-fir forests with sagebrush/grass openings on "
                "valley floor. Surface fire 1-2 mph in timber, 2-4 mph in sage openings. Crown "
                "fire potential high in dense lodgepole stands with ladder fuels. Beetle-kill "
                "standing dead timber increases torching risk. High elevation moderates fire season "
                "length but concentrated July-September window produces intense events."
            ),
            "spotting_distance": (
                "1-3 miles in forested terrain. Mountain terrain amplifies convective columns — "
                "the 2024 Wapiti Fire produced massive pyrocumulus visible from Boise. Long-range "
                "spotting across the valley floor is a primary concern for Stanley."
            ),
        },
        "infrastructure_vulnerabilities": {
            "water_system": (
                "Small community water system. Limited fire flow capacity. No hydrants in "
                "surrounding areas. Sawtooth NRA ranger station has some water infrastructure "
                "but not designed for community firefighting. River drafting possible but requires "
                "equipment positioning."
            ),
            "power": (
                "Idaho Power single-transmission feed through remote, forested terrain. No "
                "redundancy. Extended outages common during fire events (Hwy 21 corridor poles "
                "burn). Limited backup generation — Stanley is essentially off-grid during outages. "
                "Winter power loss in -40F conditions is life-threatening."
            ),
            "communications": (
                "Very limited cellular coverage. One cell tower serves Stanley area. Satellite "
                "internet for some residents. USFS radio network provides best communications. "
                "Emergency notification relies on Custer County Sheriff and word-of-mouth in this "
                "tiny community. Landline service intermittent."
            ),
            "medical": (
                "No hospital, no clinic. Sawtooth Wilderness medical services are volunteer-based. "
                "Nearest hospital is Challis (60 miles) with basic ER, or Boise (130 miles) for "
                "trauma. Air ambulance extremely weather-dependent at 6,250 ft in mountain valley. "
                "Medical evacuation during active fire may be impossible."
            ),
        },
        "demographics_risk_factors": {
            "population": 120,
            "seasonal_variation": (
                "Year-round pop ~120. Summer tourism swells effective population to 2,000-5,000 "
                "with campgrounds, lodges, outfitters, and Redfish Lake visitors. Winter population "
                "drops below 100. Visitors are overwhelmingly unfamiliar with evacuation procedures "
                "and terrain hazards. Many recreating in backcountry miles from any road."
            ),
            "elderly_percentage": "~15% (65+), hardy year-round residents",
            "mobile_homes": (
                "Some older mobile/manufactured homes and seasonal cabins. Many structures are "
                "historic wood-frame construction. Limited fire-code compliance in unincorporated area."
            ),
            "special_needs_facilities": (
                "Stanley Community School (K-8, ~20 students). No assisted living. No medical "
                "facilities. Seasonal outfitter camps and lodges house visitors who may have "
                "mobility limitations. Backcountry recreators (hikers, rafters) can be cut off "
                "from evacuation routes by fire."
            ),
        },
    },

    # =========================================================================
    # MONTANA (11 cities)
    # =========================================================================

    # =========================================================================
    # 4. HAMILTON, MT — Bitterroot Valley
    # =========================================================================
    "hamilton_mt": {
        "center": [46.2468, -114.1594],
        "terrain_notes": (
            "Hamilton (pop ~4,659) is the county seat of Ravalli County, situated at 3,570 ft "
            "elevation in the heart of the Bitterroot Valley of southwestern Montana. The valley "
            "extends ~95 miles from Lost Trail Pass (Idaho border) north to Missoula, with the "
            "Bitterroot Range (steep, heavily forested, 7,000-9,000 ft peaks) to the west and the "
            "Sapphire Mountains (more rounded, drier, less forested) to the east. The Bitterroot "
            "River flows north through the valley floor. Hamilton sits at a moderate-width point in "
            "the valley where deep canyons from the Bitterroot Range — including Blodgett Canyon, "
            "Mill Creek, and Sleeping Child — channel directly toward town. The 2000 Bitterroot "
            "fire season was among the most catastrophic in US history: 356,000 acres burned, 70 homes "
            "and 170 structures destroyed, 1,500+ evacuated, and the valley was declared a national "
            "disaster area. On July 31, 2000, a single dry lightning storm ignited 70+ fires in the "
            "Bitterroot Mountains. On 'Black Sunday' (Aug 6, 2000), multiple fires merged into massive "
            "complexes. Ravalli County is one of Montana's fastest-growing counties (pop 44,174), with "
            "84.4% of residents living in rural areas — many building homes in the trees. Over 162,000 "
            "acres of high-risk forest remain in the valley's WUI."
        ),
        "key_features": [
            {"name": "Bitterroot Range", "bearing": "W", "type": "mountain_range",
             "notes": "Longest single range in Rockies; steep faces, deep canyons, heavily forested; within Bitterroot NF (1.6M acres); 50% designated wilderness"},
            {"name": "Sapphire Mountains", "bearing": "E", "type": "mountain_range",
             "notes": "More rounded, drier, less forested than Bitterroots; grass/shrub fire regime; faster fire spread on open terrain"},
            {"name": "Bitterroot River", "bearing": "N-S through valley", "type": "river",
             "notes": "Primary drainage; north-flowing; riparian corridor but insufficient as crown fire barrier"},
            {"name": "Blodgett Canyon", "bearing": "W", "type": "canyon",
             "notes": "Deep glacial canyon cutting into Bitterroots; dramatic fire runs possible down-canyon toward valley homes"},
            {"name": "Sleeping Child drainage", "bearing": "SW", "type": "drainage",
             "notes": "2000 Sleeping Child fire burned 38,000 acres; drainage channels directly toward Hamilton area"},
            {"name": "Bitterroot National Forest", "bearing": "W/S", "type": "national_forest",
             "notes": "1.6 million acres; 3 ranger districts (Stevensville, Darby/Sula, West Fork); largest continuous pristine wilderness in lower 48"},
        ],
        "elevation_range_ft": [3400, 7500],
        "wui_exposure": "extreme",
        "historical_fires": [
            {"name": "Bitterroot Fires of 2000 (complex)", "year": 2000, "acres": 356000,
             "details": "Most expensive fire season in US history at the time; 70+ fires ignited by single lightning storm July 31; Black Sunday (Aug 6) saw massive blowup; 70 homes, 170 structures, 94 vehicles destroyed; 1,500+ evacuated; valley declared national disaster area; millions in suppression costs and property losses"},
            {"name": "Sleeping Child Fire", "year": 2000, "acres": 38000,
             "details": "Landmark fire in the Sleeping Child drainage southwest of Hamilton; part of the 2000 complex; threatened valley floor communities"},
            {"name": "Valley Complex Fire", "year": 2000, "acres": 120000,
             "details": "Multiple fires merged in West Fork Bitterroot River on Aug 6; largest single complex in the 2000 season"},
            {"name": "Bass Creek Fire", "year": 2000, "acres": 4000,
             "details": "Burned closer to valley floor near Florence; demonstrated fire reaching populated valley bottom"},
        ],
        "evacuation_routes": [
            {"route": "US-93 North (toward Missoula)", "direction": "N", "lanes": 2,
             "bottleneck": "Single primary highway for entire valley; bottleneck at Florence and Lolo",
             "risk": "The ONLY major evacuation route for entire southern Bitterroot Valley; 47 miles to Missoula; 1,500+ people evacuated on this road in 2000"},
            {"route": "US-93 South (toward Darby/Lost Trail Pass)", "direction": "S", "lanes": 2,
             "bottleneck": "Road narrows through Darby; Lost Trail Pass (7,014 ft) to Idaho",
             "risk": "Leads deeper into fire-prone country; 2000 fires burned on both sides of this road; Idaho side equally remote"},
            {"route": "MT-38 West (Skalkaho Pass to Anaconda)", "direction": "E", "lanes": 2,
             "bottleneck": "Unpaved mountain road; Skalkaho Pass (7,260 ft); seasonal closure",
             "risk": "Not suitable for mass evacuation; closed in winter; narrow switchbacks"},
            {"route": "MT-269 (Eastside Highway)", "direction": "N", "lanes": 2,
             "bottleneck": "Narrow rural road through farmland and small towns",
             "risk": "Parallel to US-93 on east side of valley; provides alternative but same general direction"},
        ],
        "fire_spread_characteristics": {
            "primary_wind_regime": (
                "Afternoon thermal up-valley (south-to-north) winds at 10-20 mph driving fire north "
                "through the Bitterroot corridor. Strong westerly canyon winds from Bitterroot Range "
                "drainages during fire events. The 2000 fires demonstrated fire creating its own weather "
                "with pyroconvection columns and erratic wind shifts."
            ),
            "critical_corridors": [
                "West Fork Bitterroot — primary fire approach from the south/southwest wilderness",
                "Blodgett/Mill Creek canyons — channeled fire runs directly toward Hamilton",
                "Sleeping Child drainage — proven catastrophic fire corridor in 2000",
                "Valley floor grass/sage — allows rapid lateral fire spread between canyons",
                "US-93 corridor — timber and homes along highway create continuous fuel",
            ],
            "rate_of_spread_potential": (
                "Extreme. The 2000 Bitterroot fires set the national standard for catastrophic WUI "
                "fire events. Black Sunday (Aug 6, 2000) saw multiple fires merge and run tens of "
                "thousands of acres in a single day. Canyon winds can drive crown fire at 2-5 mph "
                "sustained through heavy timber. Grass fire on valley floor can spread at 10+ mph."
            ),
            "spotting_distance": (
                "1-3 miles in Bitterroot Range canyon wind events; the 2000 fires threw embers "
                "across the valley floor. Spot fires ignited ahead of the main fire front were a "
                "primary mechanism of the rapid fire spread during the complex."
            ),
        },
        "infrastructure_vulnerabilities": {
            "water_system": (
                "Hamilton municipal water from wells. Rural areas on private wells with limited fire flow. "
                "2000 fires demonstrated water system overwhelmed when dozens of structures burning "
                "simultaneously. Rural volunteer fire departments have limited water tender capacity."
            ),
            "power": (
                "Ravalli Electric Cooperative; single transmission line through valley vulnerable to "
                "fire damage. Extended outages during 2000 fires. Many rural residences on single-line "
                "power feeds."
            ),
            "communications": (
                "Limited cell coverage in canyon areas and Bitterroot Range. Rural areas rely on "
                "landlines and radio. 2000 fires overwhelmed communications systems; evacuation "
                "notifications were delayed for some areas."
            ),
            "medical": (
                "Bitterroot Health (Marcus Daly Memorial Hospital) — small community hospital (~25 beds) "
                "founded 1931. Only hospital for entire Bitterroot Valley south of Missoula. "
                "Nearest Level II trauma center is 47 miles north in Missoula."
            ),
        },
        "demographics_risk_factors": {
            "population": 4659,
            "seasonal_variation": (
                "Ravalli County pop 44,174; one of Montana's fastest-growing counties. Summer recreation "
                "and tourism increase valley population. Many seasonal/second homes in forested WUI areas."
            ),
            "elderly_percentage": "~28% over 65 (median age 50.2 — significantly higher than state average; oldest-skewing county in MT)",
            "mobile_homes": (
                "Significant mobile home presence throughout valley; rural lots with single-wide "
                "units common; 84.4% of county residents in rural areas, many in fire-vulnerable settings."
            ),
            "special_needs_facilities": (
                "Marcus Daly Memorial Hospital, several assisted living facilities, Ravalli County "
                "fairgrounds (evacuation staging), rural schools scattered through valley."
            ),
        },
    },

    # =========================================================================
    # 2. HELENA, MT — State Capital
    # =========================================================================
    "helena_mt": {
        "center": [46.5958, -112.0270],
        "terrain_notes": (
            "Helena, Montana's state capital, sits at ~4,058 ft elevation in a broad valley between "
            "the Big Belt Mountains to the east and the Continental Divide/Helena National Forest to "
            "the west and south. The city was founded during the 1864 gold rush in Last Chance Gulch, "
            "and the historic downtown sits in a narrow gulch at the base of Mount Helena (5,468 ft), "
            "which rises 1,300 ft directly above the city center. The South Hills immediately south "
            "of town are heavily forested with ponderosa pine and Douglas fir extending into the "
            "Helena-Lewis and Clark National Forest. Ten Mile Creek and Prickly Pear Creek drain "
            "through the western and eastern portions of the city respectively. The Sleeping Giant "
            "Wilderness Study Area lies 30 miles north along the Missouri River, with elevations "
            "from 3,600 to 6,800 ft. Helena has experienced repeated wildfire threats: the 2021 "
            "fire season brought the Rock Creek Fire (2,560 acres), Woods Creek Fire (12,000 acres), "
            "and Harris Mountain Fire (25,000 acres) all burning simultaneously near the city. "
            "A 2023 fire on Mount Helena itself burned 18 acres within the city park. The South Hills "
            "trail system area has active USFS prescribed burn programs specifically to reduce WUI risk."
        ),
        "key_features": [
            {"name": "Mount Helena", "bearing": "SW", "type": "mountain/city_park",
             "notes": "5,468 ft summit, 620-acre city park; 2023 fire burned 18 acres on slopes; ponderosa pine/grass; directly above downtown"},
            {"name": "South Hills", "bearing": "S", "type": "forested_WUI",
             "notes": "Dense ponderosa/Douglas fir extending from residential neighborhoods into Helena NF; active prescribed burn area; camping closures due to fire risk"},
            {"name": "Sleeping Giant WSA", "bearing": "N", "type": "wilderness_study_area",
             "notes": "30 mi north; 3,600-6,800 ft elevation; half forested; 20+ creeks; fire smoke funnels south toward Helena"},
            {"name": "Helena-Lewis and Clark NF", "bearing": "S/W", "type": "national_forest",
             "notes": "Surrounds Helena on south and west; mixed conifer forests; significant fire history including 1988 Elkhorn fire (37,000 acres)"},
            {"name": "Ten Mile Creek", "bearing": "W", "type": "drainage",
             "notes": "Major western drainage; municipal watershed; forested corridor providing fire pathway toward city"},
            {"name": "Elkhorn Mountains", "bearing": "SE", "type": "mountain_range",
             "notes": "1988 fire from faulty jeep exhaust grew from truck-sized to 37,000 acres; steep terrain, 2,500 firefighters deployed"},
        ],
        "elevation_range_ft": [3800, 5500],
        "wui_exposure": "high",
        "historical_fires": [
            {"name": "Harris Mountain Fire", "year": 2021, "acres": 25000,
             "details": "Burned north of Helena; 13% contained at peak; simultaneous with Rock Creek and Woods Creek fires creating multi-front threat"},
            {"name": "Woods Creek Fire", "year": 2021, "acres": 12000,
             "details": "East of Helena; active at northwest and southeast corners; evacuation orders for Highway 284 area; highway closed"},
            {"name": "Rock Creek Fire", "year": 2021, "acres": 2560,
             "details": "North of Helena near Highway 287; Lewis & Clark County evacuated residents along Craig River Road; I-15 partially closed"},
            {"name": "Mount Helena Fire", "year": 2023, "acres": 18,
             "details": "Human-caused fire within Mount Helena City Park; demonstrated direct urban ignition risk; fire mitigation efforts praised"},
            {"name": "Elkhorn Mountains Fire", "year": 1988, "acres": 37000,
             "details": "Started from faulty jeep exhaust in Warm Springs Creek; grew from truck-sized to 2,500 acres overnight; 2,500 firefighters"},
            {"name": "North Helena Fire", "year": 1988, "acres": 34000,
             "details": "Late-season wildfire north of Sleeping Giant area; significant acreage in rugged terrain"},
        ],
        "evacuation_routes": [
            {"route": "I-15 North (toward Great Falls)", "direction": "N", "lanes": 4,
             "bottleneck": "Montana City interchange; merge with US-12 traffic",
             "risk": "2021 Rock Creek Fire forced partial I-15 closure; fires north of Helena can cut this route"},
            {"route": "I-15 South (toward Butte)", "direction": "S", "lanes": 4,
             "bottleneck": "Boulder Hill grade; construction zones",
             "risk": "South Hills fires could threaten southern approaches; generally most reliable evacuation route"},
            {"route": "US-12 West (toward Missoula)", "direction": "W", "lanes": 2,
             "bottleneck": "MacDonald Pass (6,325 ft); narrow, winding 2-lane over Continental Divide",
             "risk": "Helena NF fires along corridor; winter conditions make pass treacherous; long detour if closed"},
            {"route": "US-12 East (toward Townsend)", "direction": "E", "lanes": 2,
             "bottleneck": "Canyon Ferry Road narrows; limited passing zones",
             "risk": "Big Belt Mountain fires could close this corridor; serves as access to Canyon Ferry Dam area"},
            {"route": "Highway 284 (toward York/Trout Creek)", "direction": "NE", "lanes": 2,
             "bottleneck": "Narrow canyon road; limited capacity",
             "risk": "2021 Woods Creek Fire forced full closure; dead-end road beyond York for many residents"},
        ],
        "fire_spread_characteristics": {
            "primary_wind_regime": (
                "Southwest winds dominate, channeled through gulches and valleys. Chinook winds from "
                "the west over the Continental Divide can produce rapid fire growth. Afternoon thermal "
                "winds drive upslope fire behavior on Mount Helena and South Hills. Valley inversions "
                "common in fall, trapping smoke."
            ),
            "critical_corridors": [
                "South Hills — direct forested WUI connection from Helena NF into residential areas",
                "Ten Mile Creek — western drainage corridor channeling fire toward city",
                "Last Chance Gulch — narrow historic downtown in fire-funneling terrain",
                "Prickly Pear Valley — eastern approach with grass fire potential",
                "Mount Helena City Park — 620 forested acres immediately above downtown",
            ],
            "rate_of_spread_potential": (
                "Moderate to high. South Hills terrain produces classic upslope fire runs in afternoon "
                "heating. Grass-to-timber transition on Mount Helena allows rapid fire development. "
                "The 1988 Elkhorn fire demonstrated overnight explosive growth (truck-sized to 2,500 acres) "
                "in similar fuel types."
            ),
            "spotting_distance": (
                "0.25-0.75 miles typical in ponderosa pine/Douglas fir fuel types; "
                "higher in Chinook wind events. South Hills fires could spot into residential "
                "neighborhoods within minutes."
            ),
        },
        "infrastructure_vulnerabilities": {
            "water_system": (
                "City of Helena water from Ten Mile Creek watershed and Missouri River wells. "
                "Ten Mile treatment plant vulnerable to fire in upper watershed. South Hills "
                "residential areas on higher-elevation pressure zones may lose pressure during "
                "high fire-flow demand."
            ),
            "power": (
                "NorthWestern Energy grid; transmission lines cross Helena NF and South Hills. "
                "State government buildings have backup generators but residential areas do not. "
                "Extended outages possible if fire damages transmission infrastructure."
            ),
            "communications": (
                "State capital has robust government communications infrastructure. Cell towers "
                "on Mount Helena and surrounding peaks are fire-exposed. Emergency Operations "
                "Center in Lewis and Clark County courthouse."
            ),
            "medical": (
                "St. Peter's Health (~120 beds) is the sole hospital; Level III trauma center. "
                "State capital location provides access to additional government emergency resources "
                "but single-hospital city is vulnerable to surge events during fire evacuations."
            ),
        },
        "demographics_risk_factors": {
            "population": 34729,
            "seasonal_variation": (
                "State government workforce (largest employer) is year-round. Carroll College adds "
                "~1,500 students. Tourism moderate in summer. Population relatively stable but "
                "surrounding Lewis and Clark County (pop 70,973) residents evacuate into Helena."
            ),
            "elderly_percentage": "~18% over 65 (median age 40.4, higher than state average)",
            "mobile_homes": (
                "Mobile home parks in Montana City area south of Helena and along US-12 east corridor; "
                "moderate concentration relative to city size."
            ),
            "special_needs_facilities": (
                "Montana State Capitol complex, state offices, Montana State Prison (Deer Lodge, 50 mi), "
                "multiple assisted living facilities, Carroll College dormitories, Helena Regional Airport."
            ),
        },
    },

    # =========================================================================
    # 3. KALISPELL / WHITEFISH, MT — Flathead Valley
    # =========================================================================
    "kalispell_whitefish_mt": {
        "center": [48.2148, -114.3130],
        "terrain_notes": (
            "Kalispell (pop ~31,000) and Whitefish (pop ~7,750) sit in the broad Flathead Valley "
            "of northwest Montana, the southern extension of the Rocky Mountain Trench that runs "
            "from the Yukon Territory into Montana. Kalispell lies at ~2,956 ft elevation on the "
            "valley floor, while Whitefish is at 3,028 ft at the northern tip of the valley, just "
            "25 miles west of Glacier National Park. The Flathead National Forest (2.4 million acres) "
            "dominates the landscape to the north, east, and west. Flathead Lake, the largest natural "
            "freshwater lake west of the Mississippi, lies to the south. The valley was formed by "
            "glaciers flowing down the Trench from British Columbia, leaving a flat floor surrounded "
            "by steep, forested mountains. Flathead County's WUI amounts to 37% of total land area — "
            "the largest landowner is the US Forest Service. The 2003 fire season devastated the region: "
            "the Robert Fire burned 57,570 acres in Glacier NP and Flathead NF, forcing evacuations of "
            "West Glacier and Apgar. The valley has experienced extreme growth with homes built within "
            "or adjacent to forest lands, often on steep terrain or hilltops. Decades of fire suppression "
            "have created dangerous fuel accumulations. The fire regime is classified as mixed to high "
            "severity, meaning large fires can be stand-replacing crown fires."
        ),
        "key_features": [
            {"name": "Flathead National Forest", "bearing": "N/E/W", "type": "national_forest",
             "notes": "2.4 million acres surrounding valley; mixed to high severity fire regime; decades of fuel buildup from suppression"},
            {"name": "Glacier National Park", "bearing": "NE", "type": "national_park",
             "notes": "25 mi from Whitefish; 2003 fires burned 13% of park (136,000 acres); fire source for NW winds"},
            {"name": "Flathead Lake", "bearing": "S", "type": "lake",
             "notes": "Largest natural freshwater lake W of Mississippi; southern boundary of valley; potential firebreak"},
            {"name": "Whitefish Range", "bearing": "NW", "type": "mountain_range",
             "notes": "Active USFS fuel mitigation project ($2M+); steep forested terrain directly above Whitefish; WUI exposure"},
            {"name": "Swan Range", "bearing": "E", "type": "mountain_range",
             "notes": "Eastern valley wall; steep, heavily forested; fires here produce smoke that settles into valley"},
            {"name": "Flathead River", "bearing": "through valley", "type": "river",
             "notes": "North and Middle Forks converge in valley; riparian corridors but not effective firebreaks for crown fire"},
            {"name": "Columbia Falls", "bearing": "NE of Kalispell", "type": "community",
             "notes": "Pop 4,688; gateway community to Glacier; directly in path of NE-origin fires"},
        ],
        "elevation_range_ft": [2900, 7500],
        "wui_exposure": "extreme",
        "historical_fires": [
            {"name": "Robert Fire", "year": 2003, "acres": 57570,
             "details": "Human-caused; burned in Glacier NP and Flathead NF; jumped North Fork Flathead River; forced evacuations of Lake McDonald Valley, West Glacier, and Apgar; $68M+ cost for 2003 fire season in park; 5,000-acre tactical burnout saved communities"},
            {"name": "Wedge Canyon Fire", "year": 2003, "acres": 53314,
             "details": "Part of 2003 fire complex in Glacier NP; 26 wildfires scorched ~13% of park that season"},
            {"name": "Moose Fire", "year": 2001, "acres": 71000,
             "details": "Burned in Flathead NF north of Glacier; demonstrated scale of potential fire events in the region"},
            {"name": "Red Meadow Fire", "year": 2003, "acres": 17000,
             "details": "Additional 2003 fire season blaze in Flathead NF; contributed to regional smoke and resource strain"},
        ],
        "evacuation_routes": [
            {"route": "US-93 South (toward Polson/Missoula)", "direction": "S", "lanes": 4,
             "bottleneck": "Kalispell Bypass; Flathead Lake narrows road to 2 lanes at Elmo/Polson",
             "risk": "Long distance to next major city (Missoula, 120 mi); fires along corridor possible"},
            {"route": "US-93 North (toward Eureka/Canada)", "direction": "N", "lanes": 2,
             "bottleneck": "2-lane road; Whitefish congestion; narrow Tobacco Valley",
             "risk": "Heads deeper into forested North Fork area; limited Canadian border crossing capacity"},
            {"route": "US-2 East (toward Glacier/Browning)", "direction": "E", "lanes": 2,
             "bottleneck": "Marias Pass (5,213 ft); narrow canyon sections",
             "risk": "2003 fires closed areas along this corridor; passes through fire-prone Flathead NF"},
            {"route": "US-2 West (toward Libby/Idaho)", "direction": "W", "lanes": 2,
             "bottleneck": "2-lane through mountainous terrain; limited passing",
             "risk": "Remote corridor through Kootenai NF; fire can close road for extended periods"},
            {"route": "MT-35 (east shore Flathead Lake)", "direction": "SE", "lanes": 2,
             "bottleneck": "Narrow lakeside road; limited capacity",
             "risk": "Scenic route with steep terrain; not suitable for mass evacuation"},
        ],
        "fire_spread_characteristics": {
            "primary_wind_regime": (
                "Prevailing westerly and southwesterly winds channel through the Rocky Mountain Trench. "
                "Strong downslope (Chinook/foehn) winds from the Continental Divide can produce extreme "
                "fire behavior. Valley thermals create afternoon up-valley winds. Pacific weather systems "
                "bring dry lightning in July-August."
            ),
            "critical_corridors": [
                "Whitefish Range — steep forested slopes directly above Whitefish residential areas",
                "North Fork Flathead — fire approach corridor from Glacier NP area",
                "Swan Valley — eastern approach with continuous forest fuel",
                "Stillwater corridor — river valley connecting wildlands to Kalispell suburbs",
                "Columbia Falls gateway — funnel point between park and valley communities",
            ],
            "rate_of_spread_potential": (
                "High to extreme. Mixed to high severity fire regime means crown fires are expected. "
                "The Robert Fire demonstrated rapid growth (7,000 acres in first few days) and ability "
                "to jump major rivers. Decades of suppression have created ladder fuels throughout "
                "the valley's forested WUI."
            ),
            "spotting_distance": (
                "1-2+ miles in wind-driven crown fire events. Robert Fire jumped the North Fork "
                "Flathead River. Conifer bark and ember transport in Trench winds can carry ignition "
                "sources well ahead of the fire front."
            ),
        },
        "infrastructure_vulnerabilities": {
            "water_system": (
                "Kalispell municipal water from wells and Ashley Creek watershed. Whitefish draws from "
                "Whitefish Lake. Both systems adequate for normal operations but simultaneous structure "
                "fires in WUI areas could exceed capacity, especially for outlying developments on "
                "private wells."
            ),
            "power": (
                "Flathead Electric Cooperative and NorthWestern Energy. Transmission lines traverse "
                "Flathead NF; vulnerable to fire damage. Glacier Park area has limited redundant power "
                "infrastructure. Rolling outages possible during extreme fire events."
            ),
            "communications": (
                "Cell coverage good in valley floor but gaps in surrounding mountains and drainages. "
                "North Fork area has extremely limited communications. Emergency radio repeaters on "
                "mountain peaks are fire-exposed."
            ),
            "medical": (
                "Logan Health Medical Center in Kalispell (~577 beds systemwide across 5 hospitals) is the "
                "regional referral center with 400+ physicians. Logan Health-Whitefish is a 25-bed "
                "Critical Access Hospital serving 30,000+ people. North Valley Hospital in Whitefish "
                "provides additional capacity. Regional center adequate but 100+ mile distance to next "
                "major medical center (Missoula)."
            ),
        },
        "demographics_risk_factors": {
            "population": 38750,
            "seasonal_variation": (
                "Massive summer tourism surge from Glacier National Park (3+ million visitors/year). "
                "Whitefish Mountain Resort brings winter tourism. Summer population in broader Flathead "
                "Valley may double. Tourist population unfamiliar with fire evacuation routes."
            ),
            "elderly_percentage": "~18% over 65 (Whitefish skews older/wealthier; Kalispell more mixed)",
            "mobile_homes": (
                "Scattered mobile home parks throughout valley, especially along US-93 corridor "
                "between Kalispell and Whitefish and in Evergreen area east of Kalispell."
            ),
            "special_needs_facilities": (
                "Logan Health hospital complex, multiple assisted living/memory care facilities, "
                "Flathead Valley Community College, seasonal workforce housing (limited quality), "
                "Glacier Park lodges and campgrounds with transient populations."
            ),
        },
    },

    # =========================================================================
    # 10. LINCOLN, MT — Continental Divide Community
    # =========================================================================
    "lincoln_mt": {
        "center": [46.9547, -112.6811],
        "terrain_notes": (
            "Lincoln (pop ~868) is an unincorporated community in Lewis and Clark County at 4,536 ft "
            "elevation in the upper Blackfoot River valley, astride Montana Highway 200 near the "
            "Continental Divide. The community extends approximately 6 miles east and 3 miles west "
            "along the Blackfoot River valley, surrounded by the Helena-Lewis and Clark National Forest. "
            "Highway 200 — the longest state highway in Montana at 706.6 miles — is the ONLY road "
            "through Lincoln, running northeast 87 miles over the Continental Divide to Great Falls "
            "and west 77 miles to Missoula. The community is one of Montana's most remote and isolated "
            "towns, with the nearest hospital 60+ miles away in either direction. The Continental "
            "Divide bisects the region, with the Sun River Canyon on the east slope and the Blackfoot "
            "Valley on the west. Fire history is extensive: the 2017 Alice Creek Fire burned 29,252 "
            "acres north of Lincoln in the Helena NF (part of the record 1.25-million-acre 2017 MT "
            "fire season), the Park Creek Fire started 2 miles north of Lincoln that same year, and "
            "the 2024 Black Mountain Fire forced evacuation orders for residents north of Highway 200. "
            "The economy has traditionally centered on timber harvesting and ranching. The community "
            "has a humid continental/subarctic climate with 85.4 inches of annual snowfall."
        ),
        "key_features": [
            {"name": "Continental Divide", "bearing": "NE", "type": "geographic_divide",
             "notes": "Bisects the region; fires can cross the divide; Alice Creek Fire did so in 2017; major weather boundary"},
            {"name": "Blackfoot River valley", "bearing": "E-W", "type": "river_valley",
             "notes": "Community spreads along 9-mile stretch of valley; forested hillsides on both sides; smoke pools in inversions"},
            {"name": "Helena-Lewis and Clark NF", "bearing": "surrounding", "type": "national_forest",
             "notes": "Forest surrounds community in all directions; continuous fuel; fire can approach from any direction"},
            {"name": "Montana Highway 200", "bearing": "E-W", "type": "highway",
             "notes": "Only road through community; 706.6 mi total length; 77 mi to Missoula, 87 mi to Great Falls; closure isolates Lincoln completely"},
            {"name": "Stonewall Creek area", "bearing": "N", "type": "subdivision/drainage",
             "notes": "Subdivision north of town; 2024 Black Mountain Fire approached from NW; evacuation orders issued"},
            {"name": "Alice Creek drainage", "bearing": "N", "type": "drainage",
             "notes": "Site of 2017 29,252-acre fire; fire crossed Continental Divide; rerouted CDT hikers to Hwy 200"},
        ],
        "elevation_range_ft": [4400, 7500],
        "wui_exposure": "high",
        "historical_fires": [
            {"name": "Alice Creek Fire", "year": 2017, "acres": 29252,
             "details": "Lightning-caused; north of Lincoln in Helena NF; crossed the Continental Divide; part of record 2017 MT fire season (1.25M acres statewide); rerouted Continental Divide Trail hikers"},
            {"name": "Park Creek Fire", "year": 2017, "acres": 5000,
             "details": "Lightning-caused; started just 2 miles north of Lincoln; Stonewall Mountain Lookout trail closures; concurrent with Alice Creek creating multi-front threat"},
            {"name": "Black Mountain Fire", "year": 2024, "acres": 185,
             "details": "Several miles NW of Lincoln; evacuation orders for residents north of Highway 200; firefighters stopped spread toward Stonewall Creek subdivision"},
            {"name": "Canyon Creek Fire", "year": 1988, "acres": 250000,
             "details": "Massive fire in the region; contributed to the understanding of blowup fire behavior; 30-year retrospective published in local media"},
        ],
        "evacuation_routes": [
            {"route": "MT-200 West (toward Missoula)", "direction": "W", "lanes": 2,
             "bottleneck": "77 miles of 2-lane highway through forested Blackfoot Valley; passes through minimal communities",
             "risk": "Only westbound escape; Blackfoot Valley fires can close road; 1.5+ hours to Missoula in best conditions; fire approach from either side of valley threatens road"},
            {"route": "MT-200 East (toward Great Falls)", "direction": "NE", "lanes": 2,
             "bottleneck": "87 miles over Continental Divide; Rogers Pass (5,609 ft); narrow mountain road",
             "risk": "Longest route to help; crosses Continental Divide in fire-prone terrain; winter conditions make pass extremely dangerous; Helena NF fires threaten this corridor"},
            {"route": "Local forest roads", "direction": "various", "lanes": 1,
             "bottleneck": "Gravel, gated, seasonal; dead-end into national forest",
             "risk": "Not viable for evacuation; potential entrapment hazard for unfamiliar drivers"},
        ],
        "fire_spread_characteristics": {
            "primary_wind_regime": (
                "Complex terrain-driven winds along the Continental Divide. Blackfoot Valley channels "
                "winds east-west. The Continental Divide creates its own weather with terrain-forced "
                "thunderstorms producing dry lightning — the 2017 fires were lightning-caused. "
                "Afternoon thermals drive upslope fire on valley walls."
            ),
            "critical_corridors": [
                "Alice Creek drainage — proven 29,000+ acre fire corridor north of town",
                "Blackfoot Valley — east-west corridor where town sits; channeled fire and smoke",
                "Park Creek — fire started just 2 miles from town in 2017",
                "Stonewall Creek — residential area threatened by 2024 fire from NW",
            ],
            "rate_of_spread_potential": (
                "Moderate to high. Mixed conifer forest in mountainous terrain. The Alice Creek Fire "
                "reached 29,252 acres and crossed the Continental Divide, demonstrating significant "
                "fire runs. Valley orientation can channel fire directly through the community."
            ),
            "spotting_distance": (
                "0.5-1 mile typical in mixed conifer terrain; Continental Divide winds can increase "
                "spotting distance during extreme events."
            ),
        },
        "infrastructure_vulnerabilities": {
            "water_system": (
                "Unincorporated community; limited centralized water infrastructure. Many residents "
                "on private wells. No municipal fire hydrant system. Volunteer fire department with "
                "extremely limited water supply for structural firefighting."
            ),
            "power": (
                "Lincoln Electric Cooperative; single transmission line through forested valley. "
                "Any fire in the vicinity likely causes extended power outages. No backup generation "
                "for community facilities. Nearest line crews are 60+ miles away."
            ),
            "communications": (
                "Very limited cell coverage; mountainous terrain creates extensive dead zones. "
                "Many residents rely on landlines. Emergency notifications depend on word-of-mouth "
                "and local volunteer networks. No local radio station."
            ),
            "medical": (
                "Lincoln Health Center — small rural clinic only. No hospital. Nearest hospital is "
                "St. Peter's Health in Helena (60+ miles east) or Missoula hospitals (77 miles west). "
                "Ambulance response time from nearest hospital: 1+ hour. Air evacuation severely "
                "limited by smoke, terrain, and weather. The 60+ mile distance to hospital makes "
                "Lincoln one of the most medically isolated communities in Montana."
            ),
        },
        "demographics_risk_factors": {
            "population": 868,
            "seasonal_variation": (
                "Modest summer recreation increase; Continental Divide Trail hikers pass through. "
                "Population declined from 1,005 to 868 between 2022-2023. Seasonal residents and "
                "cabin owners increase summer population somewhat."
            ),
            "elderly_percentage": "~35% over 65 (median age 56.8 — very elderly community; isolated from medical care)",
            "mobile_homes": (
                "Common housing type in Lincoln area; older manufactured homes with deferred "
                "maintenance. Limited defensible space around many structures."
            ),
            "special_needs_facilities": (
                "Small clinic only. No assisted living, no nursing facility, no pharmacy. "
                "Elderly residents with medical needs are extremely vulnerable during fire events "
                "due to isolation and distance from any hospital."
            ),
        },
    },

    # =========================================================================
    # 11. LOLO, MT — Bitterroot Gateway
    # =========================================================================
    "lolo_mt": {
        "center": [46.7576, -114.0821],
        "terrain_notes": (
            "Lolo (pop ~4,399) is a census-designated place in Missoula County at 3,198 ft elevation, "
            "positioned at the confluence of Lolo Creek and the Bitterroot River approximately 8 miles "
            "south of Missoula. The community serves as the gateway to the Bitterroot Mountains and "
            "the Lolo National Forest, and as the eastern approach to Lolo Pass (5,233 ft) — the key "
            "route into Idaho via US-12. Lolo occupies 9.63 square miles at a critical geographic "
            "pinch point where the Bitterroot Valley meets the Missoula Valley and where Lolo Creek "
            "emerges from a deep forested canyon to the west. The 2017 Lolo Peak Fire burned 53,902 "
            "acres on the western flank of Lolo Peak (9,096 ft), evacuating 3,000+ people and "
            "threatening 1,150 residences. One firefighter was killed. The fire burned 9,000 acres in "
            "a single 24-hour wind event, with strong canyon winds racing the fire eastward toward "
            "residential areas. The 2013 Lolo Creek Complex was equally terrifying: high winds down "
            "the Lolo Creek Valley turned the West Fork Two fire into a 'blow torch,' jumping the "
            "highway and merging with the Schoolhouse Fire — residents reported having no time for "
            "evacuation warnings. Five homes burned, demonstrating catastrophic WUI fire behavior. "
            "Lolo has grown 26.1% between 2011-2023, adding 1,362 people in fire-vulnerable terrain."
        ),
        "key_features": [
            {"name": "Lolo Peak", "bearing": "SW", "type": "mountain",
             "notes": "9,096 ft; highest point on Lolo NF; 2017 fire burned 53,902 acres on its flanks; iconic Missoula-area landmark"},
            {"name": "Lolo Creek", "bearing": "W", "type": "creek/canyon",
             "notes": "Deep forested canyon running west to Lolo Pass; proven fire corridor; 2013 fire blowup here; canyon winds funnel fire toward town"},
            {"name": "Bitterroot River confluence", "bearing": "E", "type": "river",
             "notes": "Lolo Creek joins Bitterroot River at Lolo; town sits at this junction; fire from either drainage threatens community"},
            {"name": "US-12 / Lolo Pass corridor", "bearing": "W", "type": "highway/pass",
             "notes": "Route to Idaho; 5,233 ft pass through Lolo NF; fire can close this highway for extended periods"},
            {"name": "US-93 corridor", "bearing": "N-S", "type": "highway",
             "notes": "Primary Bitterroot Valley highway; connects Lolo to Missoula (8 mi N) and Hamilton (39 mi S)"},
            {"name": "Lolo National Forest", "bearing": "W/S", "type": "national_forest",
             "notes": "2.3 million acres; fire danger regularly reaches 'very high' to 'extreme' in summer"},
        ],
        "elevation_range_ft": [3100, 9100],
        "wui_exposure": "extreme",
        "historical_fires": [
            {"name": "Lolo Peak Fire", "year": 2017, "acres": 53902,
             "details": "Lightning-caused on Lolo Peak July 15; 3,000+ evacuated; 1,150 residences threatened; 2 homes destroyed; firefighter Brent Witham killed; 9,000 acres burned in single wind-driven 24-hour run; fire raced eastward toward residences driven by canyon winds"},
            {"name": "Lolo Creek Complex", "year": 2013, "acres": 12000,
             "details": "West Fork Two fire became 'blow torch' in Lolo Creek Valley winds; jumped highway; merged with Schoolhouse Fire; 5 homes burned; residents had no evacuation warning time; graphic demonstration of defensible space importance"},
            {"name": "Bitterroot Fires of 2000", "year": 2000, "acres": 356000,
             "details": "Valley-wide catastrophe; Lolo at the northern end of the Bitterroot corridor was impacted by smoke and fire threat from the south"},
        ],
        "evacuation_routes": [
            {"route": "US-93 North (toward Missoula)", "direction": "N", "lanes": 4,
             "bottleneck": "Lolo/Missoula traffic merge; US-93/US-12 interchange congestion",
             "risk": "Primary and most viable evacuation route; 8 miles to Missoula; BUT Lolo Peak fire smoke filled this corridor and fire approach can threaten road"},
            {"route": "US-93 South (toward Florence/Hamilton)", "direction": "S", "lanes": 2,
             "bottleneck": "2-lane through Bitterroot Valley; shared with all valley evacuees",
             "risk": "Leads deeper into fire-prone Bitterroot Valley; contraflow to 2000 fire locations"},
            {"route": "US-12 West (toward Lolo Pass/Idaho)", "direction": "W", "lanes": 2,
             "bottleneck": "2-lane through Lolo Creek Canyon; narrow; Lolo Pass at 5,233 ft",
             "risk": "2013 fire blowup occurred in this exact canyon; fire jumped the highway; EXTREMELY DANGEROUS during fire events; proven death trap potential"},
            {"route": "Local roads (toward Florence via Eastside)", "direction": "SE", "lanes": 2,
             "bottleneck": "Rural roads through agricultural areas",
             "risk": "Alternative to US-93 but limited capacity; connects to same eventual corridors"},
        ],
        "fire_spread_characteristics": {
            "primary_wind_regime": (
                "Complex interaction of Bitterroot Valley up-valley winds (south to north), Lolo Creek "
                "canyon winds (west to east), and Missoula Valley drainage. Afternoon thermal development "
                "drives upslope fire on Lolo Peak and surrounding mountains. The 2017 fire demonstrated "
                "that strong canyon winds from the west can drive fire rapidly eastward across the mountain "
                "face toward residential areas. The 2013 Lolo Creek Complex showed that valley winds "
                "can create blow-torch conditions in the canyon, jumping roads and structures."
            ),
            "critical_corridors": [
                "Lolo Creek Canyon — proven 2013 blowup corridor; fire jumped highway",
                "Lolo Peak western slope — 2017 fire ran 9,000 acres in 24 hours toward town",
                "Bitterroot Valley approach — fire from Hamilton/Florence area runs north toward Lolo",
                "US-12 highway corridor — evacuation route and fire corridor are the same road",
            ],
            "rate_of_spread_potential": (
                "Extreme during wind events. The 2017 Lolo Peak Fire burned 5,000 acres in a single "
                "night and 9,000 in 24 hours. The 2013 Lolo Creek Complex went from manageable to "
                "catastrophic in minutes when canyon winds arrived. Rate of spread in Lolo Creek Canyon "
                "during the 2013 blowup was described as 'blowtorch' conditions."
            ),
            "spotting_distance": (
                "0.5-1.5 miles in canyon wind events. The 2013 fire spotted across the highway. "
                "Embers from Lolo Peak fire carried by canyon winds threatened residential areas "
                "well ahead of the fire front."
            ),
        },
        "infrastructure_vulnerabilities": {
            "water_system": (
                "Lolo Water District serves the community from wells. Growing population (26.1% "
                "increase 2011-2023) strains water system. Outlying homes on private wells with "
                "no fire flow. Homes in Lolo Creek canyon have extremely limited water access."
            ),
            "power": (
                "Missoula Electric Cooperative; transmission lines through forested Lolo Creek "
                "corridor and along US-93. Fire damage to power lines is common during events. "
                "No backup generation for community."
            ),
            "communications": (
                "Cell coverage adequate in town but gaps in Lolo Creek canyon and surrounding "
                "mountains. The 2013 fire demonstrated that residents received no evacuation "
                "warning before fire jumped the highway — communications failure during rapid events."
            ),
            "medical": (
                "No hospital or clinic in Lolo. Dependent on Missoula hospitals (8 miles north) — "
                "Providence St. Patrick and Community Medical Center. Response time generally adequate "
                "but fire/smoke on US-93 corridor between Lolo and Missoula can delay ambulance access. "
                "Community's proximity to Missoula is both its greatest asset and vulnerability."
            ),
        },
        "demographics_risk_factors": {
            "population": 4399,
            "seasonal_variation": (
                "Growing bedroom community for Missoula; 26.1% population increase 2011-2023. "
                "US-12 corridor to Idaho brings through-traffic. Lolo Hot Springs recreation area "
                "adds summer visitors. Many new residents may not understand local fire risk."
            ),
            "elderly_percentage": "~15% over 65 (younger than state average due to Missoula commuter population)",
            "mobile_homes": (
                "Several mobile home parks along US-93 and in Lolo area; vulnerable to fire and "
                "limited defensible space."
            ),
            "special_needs_facilities": (
                "Lolo School, volunteer fire department, small commercial district. Dependent on "
                "Missoula for all hospital, social service, and emergency management resources. "
                "Rapid growth (1,362 new residents) may outpace emergency services capacity."
            ),
        },
    },

    # =========================================================================
    # 1. MISSOULA, MT — "Hub of Five Valleys"
    # =========================================================================
    "missoula_mt": {
        "center": [46.8721, -113.9940],
        "terrain_notes": (
            "Missoula sits at the convergence of five mountain-ringed valleys in western Montana, "
            "at approximately 3,209 ft elevation on the floor of ancient Glacial Lake Missoula. "
            "The Clark Fork River bisects the city east-to-west, joined by the Bitterroot River "
            "from the south and Rattlesnake Creek from the north. Mount Sentinel (5,158 ft) rises "
            "immediately east of the University of Montana campus, while Mount Jumbo (4,768 ft) "
            "flanks the north side of Hellgate Canyon. The city is literally surrounded by National "
            "Forest on all sides: Lolo NF to the south and west (2.3 million acres), portions of "
            "Flathead NF to the north, and the Rattlesnake Wilderness/NRA directly north of town. "
            "Pattee Canyon and the South Hills extend forested WUI terrain to within blocks of "
            "downtown. The five valleys (Missoula, Bitterroot, Blackfoot, Clark Fork/Hellgate, "
            "Frenchtown) all funnel toward the city, creating complex wind channeling that can "
            "drive fire and trap smoke in inversions. The 2017 fire season demonstrated this when "
            "the Lolo Peak, Rice Ridge, and other fires filled the valley with hazardous smoke "
            "for weeks. Missoula County's populated areas have greater wildfire risk than 84% of "
            "Montana counties. With 78,000+ residents and the state's second-largest metro area, "
            "Missoula represents the highest-consequence WUI scenario in Montana."
        ),
        "key_features": [
            {"name": "Mount Sentinel", "bearing": "E", "type": "mountain",
             "notes": "5,158 ft, rises directly above UM campus; steep grass/timber slopes, 1985 Hellgate Canyon fire burned here; the iconic 'M' trail"},
            {"name": "Mount Jumbo", "bearing": "NE", "type": "mountain",
             "notes": "4,768 ft, north side of Hellgate Canyon; elk winter range; grass/shrub lower slopes transition to timber"},
            {"name": "Pattee Canyon", "bearing": "SE", "type": "canyon/WUI",
             "notes": "Heavily developed residential canyon extending into Lolo NF; dense ponderosa/Douglas fir; extreme WUI exposure"},
            {"name": "Rattlesnake Creek/Wilderness", "bearing": "N", "type": "drainage/wilderness",
             "notes": "Major drainage running north from city into 33,000-acre Rattlesnake Wilderness; residential development along lower creek"},
            {"name": "Clark Fork River", "bearing": "E-W through city", "type": "river",
             "notes": "Primary river bisecting city; potential firebreak but bridged extensively; riparian corridor"},
            {"name": "Bitterroot River confluence", "bearing": "SW", "type": "river",
             "notes": "Joins Clark Fork at west edge of city; Bitterroot Valley fires can channel smoke and fire NE toward Missoula"},
            {"name": "Lolo National Forest", "bearing": "S/W/N", "type": "national_forest",
             "notes": "2.3 million acres surrounding Missoula on three sides; mixed-severity fire regime; major fire source"},
            {"name": "Miller Creek drainage", "bearing": "SE", "type": "drainage/WUI",
             "notes": "Site of 2024 Miller Peak Fire (2,724 acres); residential development up narrow canyon into NF land"},
        ],
        "elevation_range_ft": [3100, 5200],
        "wui_exposure": "extreme",
        "historical_fires": [
            {"name": "Miller Peak Fire", "year": 2024, "acres": 2724,
             "details": "Burned 8 miles SE of Missoula in Plant Creek drainage; 600+ personnel, 19 engines, 3 helicopters; evacuation warnings for Upper Miller Creek Road residents; difficult terrain limited access and visibility"},
            {"name": "Lolo Peak Fire", "year": 2017, "acres": 53902,
             "details": "Lightning-caused fire on Lolo Peak; 3,000+ evacuated, 1,150 residences threatened, 2 homes destroyed, 1 firefighter killed; 9,000 acres burned in single 24-hr wind event; filled Missoula Valley with hazardous smoke for weeks"},
            {"name": "Lolo Creek Complex", "year": 2013, "acres": 12000,
             "details": "West Fork Two fire combined with Schoolhouse Fire when high winds barreled down Lolo Creek Valley; fire jumped highway; residents had no time for evacuation warnings; 5 homes burned"},
            {"name": "Hellgate Canyon Fire", "year": 1985, "acres": 800,
             "details": "Burned slopes of Mount Sentinel adjacent to UM campus; demonstrated direct urban fire threat"},
        ],
        "evacuation_routes": [
            {"route": "I-90 West (toward Frenchtown)", "direction": "W", "lanes": 4,
             "bottleneck": "Reserve St / Orange St on-ramps; Missoula grid congestion",
             "risk": "Smoke from Bitterroot or Lolo fires can reduce visibility on I-90 through Hellgate Canyon"},
            {"route": "I-90 East (toward Clinton/Drummond)", "direction": "E", "lanes": 4,
             "bottleneck": "Hellgate Canyon narrows I-90 between Mount Sentinel and Mount Jumbo",
             "risk": "Canyon funnels both wind and smoke; fires on either peak would threaten this corridor"},
            {"route": "US-93 South (Bitterroot Valley)", "direction": "S", "lanes": 4,
             "bottleneck": "US-93/Reserve St intersection; heavy daily traffic",
             "risk": "Evacuating toward active Bitterroot fires is counterproductive; this route leads deeper into fire-prone valley"},
            {"route": "US-93 North (toward Flathead)", "direction": "N", "lanes": 2,
             "bottleneck": "Evaro Hill grade; single road through Flathead Reservation",
             "risk": "Only viable northern escape; 2-lane road would bottleneck with mass evacuation"},
            {"route": "MT-200 East (toward Lincoln/Great Falls)", "direction": "NE", "lanes": 2,
             "bottleneck": "Bonner interchange; narrow Blackfoot River canyon",
             "risk": "Remote 2-lane highway; long distance to next population center; fire can close Blackfoot corridor"},
        ],
        "fire_spread_characteristics": {
            "primary_wind_regime": (
                "Complex valley winds driven by five converging valleys. Daytime up-valley winds from "
                "the west through Hellgate Canyon at 10-25 mph; nighttime drainage winds from side canyons. "
                "Chinook (foehn) winds in spring/fall can produce extreme fire behavior. Inversions trap smoke "
                "and create prolonged hazardous air quality events."
            ),
            "critical_corridors": [
                "Pattee Canyon — dense WUI timber directly into city neighborhoods",
                "Rattlesnake Creek — north drainage funnels fire toward university/downtown",
                "Miller Creek — SE drainage, site of 2024 fire, residential development up canyon",
                "Hellgate Canyon — east-west wind tunnel between Sentinel and Jumbo",
                "Lolo Creek corridor — SW approach, demonstrated 2013 blowup potential",
            ],
            "rate_of_spread_potential": (
                "Extreme in wind-driven canyon events. Lolo Peak Fire burned 9,000 acres in 24 hours "
                "during wind event. Lolo Creek Complex fire jumped highway in minutes. Steep slopes "
                "on Sentinel and Jumbo can produce rapid upslope runs. Grass/timber interface on "
                "mountain flanks allows fast transition from surface to crown fire."
            ),
            "spotting_distance": (
                "0.5-1.5 miles typical in canyon wind events; embers carried through Hellgate Canyon "
                "corridor. Potential for long-range spotting into urban neighborhoods from Pattee Canyon "
                "or Miller Creek drainage fires."
            ),
        },
        "infrastructure_vulnerabilities": {
            "water_system": (
                "Mountain Water Company (now Missoula Water) serves city from multiple wells and the "
                "Rattlesnake Creek watershed. Fire flow capacity generally adequate for urban core but "
                "WUI homes on dead-end canyon roads (Miller Creek, Pattee Canyon, Rattlesnake) may "
                "exceed system capacity during simultaneous structure fires."
            ),
            "power": (
                "NorthWestern Energy serves the region; transmission lines cross forested corridors "
                "vulnerable to fire damage. Power outages during smoke events affect air filtration "
                "systems. Grid reliability threatened by simultaneous fire on multiple fronts."
            ),
            "communications": (
                "Cell towers on mountain peaks (Sentinel, Jumbo, Blue Mountain) are fire-exposed. "
                "Emergency alert systems require functional cell/internet infrastructure. University "
                "of Montana campus has independent emergency notification system."
            ),
            "medical": (
                "Providence St. Patrick Hospital (~250 beds) and Community Medical Center (~150 beds) "
                "provide Level II trauma capability. Both facilities are in the valley floor and "
                "accessible, but smoke events overwhelm respiratory care capacity. The 2017 smoke "
                "season demonstrated healthcare surge challenges."
            ),
        },
        "demographics_risk_factors": {
            "population": 78204,
            "seasonal_variation": (
                "University of Montana adds ~10,000 students Sept-May. Summer tourism and outdoor "
                "recreation bring additional thousands. Peak fire season overlaps with student arrival "
                "in August/September — unfamiliar population during highest risk period."
            ),
            "elderly_percentage": "~12% over 65 (lower than state average due to university population)",
            "mobile_homes": (
                "Several mobile home parks along US-93 corridor and in Wye/Frenchtown area; "
                "concentrated vulnerability in WUI-adjacent locations."
            ),
            "special_needs_facilities": (
                "Multiple assisted living facilities, university dormitories (2,500+ students), "
                "Missoula County jail (~300 capacity), homeless shelter populations. "
                "Significant transient/unhoused population in riverfront areas."
            ),
        },
    },

    # =========================================================================
    # 9. RED LODGE, MT — Beartooth Mountains
    # =========================================================================
    "red_lodge_mt": {
        "center": [45.1857, -109.2468],
        "terrain_notes": (
            "Red Lodge (pop ~2,257) is the county seat of Carbon County, situated at 5,562 ft "
            "elevation along Rock Creek at the northern edge of the Absaroka-Beartooth Wilderness "
            "adjacent to the Beartooth Mountains in south-central Montana. The town lies in a narrow "
            "valley surrounded by steep, forested terrain rising to peaks over 12,000 ft in the "
            "Beartooths. US Route 212 runs through town and south becomes the Beartooth Highway, "
            "a 68-mile National Scenic Byway open only late May to October. The community was "
            "devastated by the 2021 Robertson Draw Fire — a human-caused fire that burned 27,556 "
            "acres south of town, destroyed 21 structures, threatened 450 homes, and cost $10.5 "
            "million. In June 2022, catastrophic flooding on Rock Creek caused historic damage: "
            "100+ homes flooded, 8 public bridges washed away, the water main was compromised "
            "(town water shut off), and portions of Highway 212 were destroyed. A $14 million "
            "renovation project is ongoing. The community has a median age of 57.9 years and "
            "median household income of $43,857 — an aging, tourism-dependent mountain town "
            "with infrastructure still recovering from back-to-back fire and flood disasters."
        ),
        "key_features": [
            {"name": "Beartooth Mountains", "bearing": "S/W", "type": "mountain_range",
             "notes": "Part of Absaroka-Beartooth Wilderness; peaks to 12,799 ft (Granite Peak, MT highest); steep terrain, mixed conifer forest"},
            {"name": "Rock Creek", "bearing": "through town", "type": "creek/drainage",
             "notes": "Runs through center of Red Lodge; 2022 flooding crested at record 7.98 ft; destroyed bridges, water main, roads"},
            {"name": "Beartooth Highway (US-212)", "bearing": "S", "type": "highway/scenic_byway",
             "notes": "68-mi National Scenic Byway; seasonal (late May-Oct); only southern egress; connects to Yellowstone via Cooke City"},
            {"name": "Absaroka-Beartooth Wilderness", "bearing": "S/SW", "type": "wilderness",
             "notes": "944,000 acres; fire suppression limited in wilderness; natural fire starts common; source of Robertson Draw Fire approach"},
            {"name": "Mount Maurice area", "bearing": "S", "type": "mountain",
             "notes": "Origin point of Robertson Draw Fire; sage/grass at base transitions to timber; rapid fire spread terrain"},
        ],
        "elevation_range_ft": [5400, 12800],
        "wui_exposure": "high",
        "historical_fires": [
            {"name": "Robertson Draw Fire", "year": 2021, "acres": 27556,
             "details": "Human-caused (spilled gasoline ignited by dirt bike spark plug); started 7 mi south of Red Lodge June 13; exploded to 24,470 acres in 3 days; 21 structures damaged; 450 homes threatened; evacuation orders south of Highway 308; $10.5M damage; felony arson charges filed"},
            {"name": "Rock Creek area fires", "year": 2006, "acres": 5000,
             "details": "Multiple fires in Rock Creek drainage; demonstrated fire approach through the primary valley toward town"},
        ],
        "evacuation_routes": [
            {"route": "MT-78 North (toward Columbus/I-90)", "direction": "N", "lanes": 2,
             "bottleneck": "2-lane highway; 60 miles to I-90 at Columbus",
             "risk": "Primary evacuation route; passes through open prairie/ranch land; generally reliable but long distance"},
            {"route": "US-212 South (Beartooth Highway)", "direction": "S", "lanes": 2,
             "bottleneck": "Seasonal road (closed Oct-May); mountain pass at 10,947 ft; extreme switchbacks",
             "risk": "NOT viable for winter evacuation; leads to extremely remote Cooke City (pop 75); 2021 Robertson Draw Fire burned along this corridor"},
            {"route": "MT-308 West (toward Belfry/Bridger)", "direction": "W", "lanes": 2,
             "bottleneck": "Narrow 2-lane; small rural communities only",
             "risk": "2021 evacuation orders covered area south of 308; limited capacity; leads to equally small communities"},
        ],
        "fire_spread_characteristics": {
            "primary_wind_regime": (
                "Valley winds channeled along Rock Creek drainage. Afternoon thermal upslope winds "
                "on Beartooth front range. Chinook winds from the west can produce extreme conditions. "
                "The Robertson Draw Fire demonstrated rapid fire spread driven by afternoon winds in "
                "sage-grass transitioning to timber."
            ),
            "critical_corridors": [
                "Rock Creek drainage — primary fire approach corridor from south/southwest",
                "Robertson Draw — proven fire corridor reaching toward Red Lodge from south",
                "West Bench — residential areas above town on slopes of Beartooth foothills",
                "Highway 212 corridor — fire approach and escape route are the same road",
            ],
            "rate_of_spread_potential": (
                "High. Robertson Draw Fire grew from ignition to 24,470 acres in 72 hours. "
                "Sage-grass fuels at lower elevations allow very rapid initial spread; transition "
                "to timber at mid-elevation creates extreme fire behavior. Steep terrain multiplies "
                "rate of spread on upslope runs."
            ),
            "spotting_distance": (
                "0.5-1.5 miles in sage-grass/timber transition zone. Embers from crown fire "
                "in Beartooth timber can spot into town's forested residential areas."
            ),
        },
        "infrastructure_vulnerabilities": {
            "water_system": (
                "Municipal water from Rock Creek watershed — ALREADY COMPROMISED by 2022 flood. "
                "Water main was cut during flooding; town water shut off entirely. $14M renovation "
                "underway but system remains fragile. Fire during construction period would be "
                "catastrophic for water supply."
            ),
            "power": (
                "Beartooth Electric Cooperative; transmission lines through forested mountain terrain. "
                "Extended outages during fire or flood events. 2022 flood damaged infrastructure still "
                "being repaired."
            ),
            "communications": (
                "Cell coverage in town; gaps in surrounding mountains and Beartooth wilderness. "
                "Emergency communications impacted by remote location."
            ),
            "medical": (
                "Beartooth Billings Clinic — critical access hospital with minimal beds. "
                "Nearest major hospital is Billings (60 miles NE on MT-78 and I-90). "
                "Helicopter evacuation limited by mountain weather. Median age of 57.9 means "
                "significant healthcare demand."
            ),
        },
        "demographics_risk_factors": {
            "population": 2257,
            "seasonal_variation": (
                "Significant tourism variation: winter population ~1,200 increasing to 1,800+ in summer. "
                "Beartooth Highway and Red Lodge Mountain ski area drive seasonal economy. "
                "Peak fire season coincides with peak tourism."
            ),
            "elderly_percentage": "~35% over 65 (median age 57.9 — extremely elderly community; highest-risk demographic for fire evacuation)",
            "mobile_homes": (
                "Moderate mobile home presence; aging housing stock typical of small Montana mountain towns."
            ),
            "special_needs_facilities": (
                "Critical access hospital, small assisted living facilities, county courthouse, "
                "vacation rentals with transient populations. Infrastructure still recovering from "
                "2022 flood — compound disaster vulnerability."
            ),
        },
    },

    # =========================================================================
    # 5. SEELEY LAKE, MT — Clearwater Valley
    # =========================================================================
    "seeley_lake_mt": {
        "center": [47.1794, -113.4847],
        "terrain_notes": (
            "Seeley Lake (pop ~1,682) is a small resort and retirement community nestled in a "
            "heavily forested valley at approximately 4,000 ft elevation in northeastern Missoula "
            "County. The community sits between the Swan Range to the east and the Mission Mountains "
            "to the west, in the Seeley-Swan Valley — an 80-mile-long glacially carved corridor. "
            "The Clearwater River flows southwest out of Seeley Lake through a chain of glacially "
            "formed lakes into the Blackfoot River. Highway 83 is the sole road through the valley, "
            "connecting small rural communities. The area supports grizzly bears, gray wolves, and "
            "diverse ecosystems from valley grasslands to subalpine forests. In 2017, the Rice Ridge "
            "Fire burned 160,000+ acres and produced what peer-reviewed research identified as the "
            "worst sustained wildfire smoke event ever measured in the United States: PM2.5 levels "
            "peaked near 1,000-1,200 ug/m3 (the EPA 'hazardous' threshold is 250.5 ug/m3), with a "
            "24-hour average reaching 623.5 ug/m3. From July 31 to September 18, 2017 — 49 straight "
            "days — the daily PM2.5 average was 220.9 ug/m3. The Missoula City-County Health Department "
            "issued an unprecedented recommendation for all residents to evacuate. University of Montana "
            "research found sustained lung function decline in residents one year after exposure. "
            "The community has a median age of 62.6 years — one of the oldest in Montana — making "
            "it exceptionally vulnerable to smoke-related health impacts."
        ),
        "key_features": [
            {"name": "Swan Range", "bearing": "E", "type": "mountain_range",
             "notes": "Eastern valley wall; steep, heavily forested; fire source for westerly wind events; peaks to 9,000+ ft"},
            {"name": "Mission Mountains", "bearing": "W", "type": "mountain_range",
             "notes": "Western valley wall; tribal wilderness; deep timber; smoke from fires pools in valley between ranges"},
            {"name": "Seeley Lake (body of water)", "bearing": "center", "type": "lake",
             "notes": "Glacially formed lake; community surrounds shoreline; limited firebreak value for crown fire"},
            {"name": "Clearwater River", "bearing": "SW", "type": "river",
             "notes": "Flows SW from Seeley Lake to Blackfoot River; drainage corridor that channels smoke"},
            {"name": "Highway 83 corridor", "bearing": "N-S", "type": "road/corridor",
             "notes": "Only through-road in 80-mile valley; no alternatives; fire closure isolates community completely"},
            {"name": "Lolo National Forest (Seeley Lake RD)", "bearing": "surrounding", "type": "national_forest",
             "notes": "Ranger station in community; forest extends in all directions; continuous heavy fuel loading"},
        ],
        "elevation_range_ft": [3900, 9100],
        "wui_exposure": "extreme",
        "historical_fires": [
            {"name": "Rice Ridge Fire", "year": 2017, "acres": 160000,
             "details": "Burned for nearly 2 months (July 31-Sept 18); produced worst sustained smoke event in US measurement history; PM2.5 peaked ~1,000-1,200 ug/m3 (4x hazardous threshold); 24-hr average reached 623.5 ug/m3; 49 consecutive days of hazardous air; health department recommended full community evacuation; UM research found persistent lung function decline in residents"},
            {"name": "Jocko Lakes Fire", "year": 2007, "acres": 36000,
             "details": "Burned west of Seeley Lake in Mission Mountains; contributed to smoke in valley"},
            {"name": "Fires of 1910 (Big Blowup)", "year": 1910, "acres": 3000000,
             "details": "Regional catastrophe burned 3 million acres across MT/ID in 2 days; Seeley-Swan Valley heavily impacted; defined US fire suppression policy for a century"},
        ],
        "evacuation_routes": [
            {"route": "MT-83 South (toward Clearwater Junction/MT-200)", "direction": "S", "lanes": 2,
             "bottleneck": "Single 2-lane road; Clearwater Junction intersection; 30 miles to MT-200",
             "risk": "THE ONLY southbound escape; fire on either side of valley can close road; smoke reduces visibility to near zero as demonstrated in 2017"},
            {"route": "MT-83 North (toward Condon/Swan Lake)", "direction": "N", "lanes": 2,
             "bottleneck": "Single 2-lane road; narrow valley; 60+ miles to Bigfork/Flathead Valley",
             "risk": "Leads deeper into remote forested valley; fire closure of MT-83 at any point isolates Seeley Lake completely"},
            {"route": "MT-200 (via Clearwater Junction)", "direction": "E/W", "lanes": 2,
             "bottleneck": "Must first reach Clearwater Junction (30 mi south on MT-83); then 2-lane highway",
             "risk": "Only connection to Missoula (60+ mi total) or Great Falls; Blackfoot Valley fire can close this route"},
        ],
        "fire_spread_characteristics": {
            "primary_wind_regime": (
                "Valley-channeled winds between Swan Range and Mission Mountains create a natural "
                "chimney effect. Afternoon up-valley thermals drive fire northward. Nighttime drainage "
                "winds reverse. Strong inversions trap smoke in the narrow valley, creating the extreme "
                "PM2.5 concentrations observed in 2017. Ridgetop winds can be dramatically different "
                "from valley-floor conditions."
            ),
            "critical_corridors": [
                "Seeley-Swan Valley — entire 80-mile corridor is continuous fuel with no breaks",
                "Clearwater drainage — smoke and fire channel SW toward Blackfoot Valley",
                "Rice Ridge/Morrell Creek — demonstrated 2017 fire approach from NE",
                "Mission Mountains west slope — fires generate extreme smoke pooling in valley",
            ],
            "rate_of_spread_potential": (
                "Moderate to high for fire spread; EXTREME for smoke impact. The Rice Ridge Fire "
                "demonstrated that even moderate fire spread in surrounding terrain can create "
                "unsurvivable air quality conditions in the valley. Crown fire in the Swan or "
                "Mission ranges would generate massive smoke production funneled into the valley."
            ),
            "spotting_distance": (
                "0.5-1.5 miles in mountain terrain; valley configuration means spotting across "
                "the community is possible from fires on either range. Bark beetle-killed timber "
                "increases ember generation."
            ),
        },
        "infrastructure_vulnerabilities": {
            "water_system": (
                "Community water district from wells. No municipal fire hydrant system outside "
                "immediate town core. Volunteer fire department with limited water tender capacity. "
                "Extended fire operations strain limited water resources."
            ),
            "power": (
                "Missoula Electric Cooperative; single transmission line through forested valley. "
                "Power outages common during fire events. No backup generation for community facilities. "
                "Extended outages isolate elderly residents dependent on medical equipment."
            ),
            "communications": (
                "Limited cell coverage; gaps in surrounding mountains. Satellite phone or ham radio "
                "may be only communication during fire events. Emergency notifications depend on "
                "functional cell infrastructure. No local radio station."
            ),
            "medical": (
                "Seeley Swan Medical Center — small clinic only; family medicine and dental. "
                "Described as 'the only spot with primary and dental care in about a 50-mile radius.' "
                "Nearest hospital is in Missoula, 60+ miles away (1+ hour drive in good conditions). "
                "No ambulance with advanced life support. Air evacuation limited by smoke conditions."
            ),
        },
        "demographics_risk_factors": {
            "population": 1682,
            "seasonal_variation": (
                "Resort community with significant summer population increase from recreationists, "
                "second-home owners, and campers in surrounding NF. Winter population drops. "
                "Peak fire season coincides with peak recreational use."
            ),
            "elderly_percentage": "~40%+ over 65 (median age 62.6 — among the oldest communities in Montana; extremely vulnerable to smoke/health impacts)",
            "mobile_homes": (
                "Significant mobile home and older cabin stock around lake and along Highway 83; "
                "many structures are seasonal/recreational with deferred maintenance."
            ),
            "special_needs_facilities": (
                "Small community clinic, volunteer fire department, no nursing home or assisted living. "
                "Elderly residents with mobility/health limitations dispersed in rural settings. "
                "Transportation assistance program available but limited capacity."
            ),
        },
    },

    # =========================================================================
    # 6. STEVENSVILLE, MT — Northern Bitterroot Valley
    # =========================================================================
    "stevensville_mt": {
        "center": [46.5100, -114.0930],
        "terrain_notes": (
            "Stevensville (pop ~2,015) is a small historic town in the northern Bitterroot Valley, "
            "flanked by the Bitterroot Range to the west and Sapphire Mountains to the east, at "
            "approximately 3,370 ft elevation. It is the home of the Stevensville Ranger District "
            "of the Bitterroot National Forest. The town sits near the Bitterroot River with canyons "
            "from the Bitterroot Range — including Bass Creek, Kootenai Creek, and St. Mary's Peak "
            "drainage — cutting directly toward the community. The Bitterroot Range west of "
            "Stevensville is the longest single mountain range in the Rocky Mountains, heavily "
            "forested with mixed conifer stands. During the 2000 Bitterroot fire season, fires "
            "threatened the Stevensville area from multiple directions; the Bass Creek Fire was one "
            "of the closer threats to the valley floor. More than 162,000 acres of high-risk forest "
            "remain in the valley's WUI. Ravalli County's rapid growth has placed many new homes "
            "'in the trees' — building in forested WUI settings without adequate defensible space."
        ),
        "key_features": [
            {"name": "Bitterroot Range", "bearing": "W", "type": "mountain_range",
             "notes": "Longest single range in Rockies; St. Mary's Peak (9,351 ft) is highest point; steep canyons channel fire toward valley"},
            {"name": "Sapphire Mountains", "bearing": "E", "type": "mountain_range",
             "notes": "Drier eastern range; grass/shrub fuel types allow fast lateral fire spread"},
            {"name": "Bass Creek", "bearing": "W", "type": "drainage",
             "notes": "2000 Bass Creek Fire (4,000 acres) demonstrated fire reaching valley floor near Stevensville"},
            {"name": "Kootenai Creek", "bearing": "W", "type": "drainage",
             "notes": "Deep canyon from Bitterroot wilderness; channeled fire approach toward community"},
            {"name": "Bitterroot River", "bearing": "through valley", "type": "river",
             "notes": "North-flowing river; limited firebreak for wind-driven fire"},
            {"name": "Stevensville Ranger District", "bearing": "surrounding", "type": "ranger_district",
             "notes": "Headquarters of Bitterroot NF Stevensville RD; manages 1.6M acres including wilderness"},
        ],
        "elevation_range_ft": [3300, 9400],
        "wui_exposure": "high",
        "historical_fires": [
            {"name": "Bitterroot Fires of 2000", "year": 2000, "acres": 356000,
             "details": "Valley-wide catastrophe; 70 homes, 170 structures, 94 vehicles destroyed across Ravalli County; 1,500+ evacuated; national disaster declaration"},
            {"name": "Bass Creek Fire", "year": 2000, "acres": 4000,
             "details": "Burned near valley floor close to Stevensville/Florence; demonstrated fire penetrating to populated valley bottom"},
            {"name": "Kootenai Creek Fire", "year": 2003, "acres": 2000,
             "details": "Burned in canyon west of Stevensville; required evacuation of canyon residents"},
        ],
        "evacuation_routes": [
            {"route": "US-93 North (toward Missoula)", "direction": "N", "lanes": 2,
             "bottleneck": "Lolo/Missoula traffic merge; 25 miles to Missoula",
             "risk": "Shared evacuation corridor with all Bitterroot Valley communities; congestion likely in mass evacuation"},
            {"route": "US-93 South (toward Hamilton/Darby)", "direction": "S", "lanes": 2,
             "bottleneck": "Leads deeper into fire-prone valley",
             "risk": "Contraflow to 2000 fire locations; evacuating south during Bitterroot Range fires is dangerous"},
            {"route": "MT-269 (Eastside Highway)", "direction": "N/S", "lanes": 2,
             "bottleneck": "Narrow rural road; limited capacity",
             "risk": "Parallel alternative to US-93 but same general limitations; crosses agricultural land"},
        ],
        "fire_spread_characteristics": {
            "primary_wind_regime": (
                "Up-valley thermal winds (south to north) during afternoon; canyon winds from Bitterroot "
                "Range drainages. Stevensville sits at a wider section of valley where multiple canyons "
                "converge, creating complex wind interactions during fire events."
            ),
            "critical_corridors": [
                "Bass Creek canyon — proven 2000 fire corridor to valley floor",
                "Kootenai Creek — deep canyon channeling fire east toward town",
                "St. Mary's Peak drainage — high-elevation fire could run downslope",
                "Valley floor grass/sage — lateral fire spread between canyon mouths",
            ],
            "rate_of_spread_potential": (
                "High in canyon wind events; moderate on valley floor. The 2000 fires demonstrated "
                "that canyon-channeled fires can reach the valley floor rapidly. Grass fire on the "
                "drier Sapphire Mountain side can spread very quickly."
            ),
            "spotting_distance": (
                "0.5-2 miles from canyon-exit fires into valley floor; similar to Hamilton-area "
                "fire behavior during 2000 season."
            ),
        },
        "infrastructure_vulnerabilities": {
            "water_system": (
                "Small municipal water system from wells. Limited fire hydrant coverage outside "
                "town core. Surrounding rural areas on private wells with no fire flow capacity."
            ),
            "power": (
                "Ravalli Electric Cooperative; single distribution lines through forested areas. "
                "Extended outages during fire events common."
            ),
            "communications": (
                "Basic cell coverage in town; gaps in canyon areas. Volunteer fire department "
                "communications. Limited emergency notification capacity for dispersed rural residents."
            ),
            "medical": (
                "No hospital. Nearest hospital is Marcus Daly Memorial in Hamilton (15 mi south) "
                "or Missoula hospitals (25 mi north). Response time for ambulance: 15-30 minutes."
            ),
        },
        "demographics_risk_factors": {
            "population": 2015,
            "seasonal_variation": (
                "Moderate summer increase from recreation. Surrounding Ravalli County rural population "
                "of 44,174 adds dispersed vulnerable residents in WUI areas."
            ),
            "elderly_percentage": "~25% over 65 (consistent with Ravalli County median age of 50.2)",
            "mobile_homes": (
                "Rural lots with mobile homes common in surrounding areas; limited defensible space."
            ),
            "special_needs_facilities": (
                "Small town with limited special needs infrastructure; senior services through "
                "Ravalli County; volunteer fire/EMS."
            ),
        },
    },

    # =========================================================================
    # 7. SUPERIOR, MT — I-90 Corridor / Clark Fork Valley
    # =========================================================================
    "superior_mt": {
        "center": [47.1916, -114.8910],
        "terrain_notes": (
            "Superior (pop ~830) is the county seat of Mineral County, a remote town at 2,844 ft "
            "elevation on the northeast side of the Bitterroot Range in western Montana, situated "
            "in the narrow Clark Fork River valley where I-90 threads through mountainous terrain. "
            "The town occupies a tight valley floor with steep, forested hillsides rising immediately "
            "on both sides. The Clark Fork River runs through the valley, and the Bitterroot Mountains "
            "to the west along the Montana/Idaho border receive enormous precipitation — nearby "
            "Lookout Pass averages 400 inches of snow annually, supporting dense timber that becomes "
            "extreme fire fuel in summer. Flat Creek Canyon runs north out of Superior, creating a "
            "critical fire corridor. The West Mullan fire demonstrated the terrain challenges: flames "
            "headed north and east into steep uninhabited hillsides while across the Clark Fork River, "
            "both timber and houses were much thicker. Fire behavior in the Superior area is described "
            "as 'dictated by weather and topography' with very steep slopes, rough terrain, and "
            "limited access for firefighters. Mineral County has a population of just 4,535 across "
            "3,459 square miles — one of Montana's most sparsely populated and remote counties."
        ),
        "key_features": [
            {"name": "Clark Fork River", "bearing": "through valley", "type": "river",
             "notes": "River runs through Superior; narrow valley constrains town; limited firebreak for slope-driven fire"},
            {"name": "Bitterroot Range (west)", "bearing": "W", "type": "mountain_range",
             "notes": "Montana/Idaho border; extreme snowfall (400 in/yr at Lookout Pass) supports dense timber = extreme fuel"},
            {"name": "Flat Creek Canyon", "bearing": "N", "type": "canyon",
             "notes": "Runs north from Superior; identified as critical fire corridor concern during West Mullan fire"},
            {"name": "I-90 corridor", "bearing": "E-W", "type": "highway/valley",
             "notes": "Major interstate follows narrow Clark Fork valley; fire and smoke regularly impact traffic; headlights required during smoke events"},
            {"name": "Lookout Pass", "bearing": "W", "type": "mountain_pass",
             "notes": "Montana/Idaho border; 4,700 ft; heavy timber; fire can close I-90 over the pass"},
        ],
        "elevation_range_ft": [2700, 6500],
        "wui_exposure": "high",
        "historical_fires": [
            {"name": "West Mullan Fire", "year": 2005, "acres": 700,
             "details": "Started as grass fire, grew to 700 acres in one night; burned toward Flat Creek Canyon; timber and houses threatened across Clark Fork River"},
            {"name": "Prospect Fire", "year": 2003, "acres": 5000,
             "details": "Burned in remote steep terrain near I-90; limited access, very steep slopes; extremely difficult suppression"},
            {"name": "Fires of 1910 (Big Blowup)", "year": 1910, "acres": 3000000,
             "details": "Regional catastrophe; Clark Fork corridor was heavily impacted; fire ran through the Bitterroots destroying towns across MT/ID border region"},
        ],
        "evacuation_routes": [
            {"route": "I-90 East (toward Missoula)", "direction": "E", "lanes": 4,
             "bottleneck": "Narrow Clark Fork canyon; 50 miles to Missoula",
             "risk": "Fire and smoke regularly close I-90; headlights-at-noon visibility documented; only high-capacity route"},
            {"route": "I-90 West (toward Lookout Pass/Idaho)", "direction": "W", "lanes": 4,
             "bottleneck": "Lookout Pass (4,700 ft); mountain grade; heavy timber both sides",
             "risk": "Fire in Bitterroots can close I-90 over the pass; Idaho side equally remote (Wallace, 30 mi)"},
            {"route": "Local forest roads", "direction": "various", "lanes": 1,
             "bottleneck": "Single-lane gravel; gated; unmaintained sections",
             "risk": "Not viable for evacuation; may serve as last-resort escape for remote residents"},
        ],
        "fire_spread_characteristics": {
            "primary_wind_regime": (
                "Valley winds channeled through the Clark Fork River corridor east-west. Slope-driven "
                "winds on steep hillsides above town. The narrow valley creates wind acceleration effects "
                "during fire events. Thermal inversions trap smoke in the valley, reducing visibility "
                "on I-90 to near zero."
            ),
            "critical_corridors": [
                "Flat Creek Canyon — primary fire corridor running north from Superior",
                "Clark Fork River valley — east-west wind tunnel; fire can run along valley",
                "West Mullan drainage — demonstrated grass-to-timber fire transition near town",
                "Lookout Pass corridor — dense timber on steep grades; potential for massive fire runs",
            ],
            "rate_of_spread_potential": (
                "High on steep slopes with heavy timber fuel loading. The West Mullan fire grew "
                "from grass fire to 700 acres overnight. Steep terrain above Superior means fires "
                "can run rapidly downhill toward town driven by slope and wind."
            ),
            "spotting_distance": (
                "0.5-1 mile typical in steep terrain; embers can cross Clark Fork River. "
                "Valley wind acceleration can increase spotting distance during blow-up events."
            ),
        },
        "infrastructure_vulnerabilities": {
            "water_system": (
                "Small municipal system. Limited water storage and fire flow capacity for a town "
                "of 830 people. Surrounding areas on wells. Volunteer fire department with "
                "limited equipment."
            ),
            "power": (
                "Single transmission line through Clark Fork corridor; highly vulnerable to fire "
                "damage. Extended outages likely during any significant fire event. No backup "
                "generation for public facilities."
            ),
            "communications": (
                "Limited cell coverage; mountainous terrain creates dead zones. I-90 corridor has "
                "better coverage but side valleys have none. Emergency communications rely on "
                "radio repeaters on fire-exposed peaks."
            ),
            "medical": (
                "Mineral Community Hospital — critical access hospital with minimal beds. "
                "Nearest major hospital is Missoula (50 miles east) or Wallace, ID (30 miles west). "
                "Ambulance response to outlying areas can exceed 30 minutes."
            ),
        },
        "demographics_risk_factors": {
            "population": 830,
            "seasonal_variation": (
                "I-90 corridor brings through-traffic but limited tourism compared to other MT towns. "
                "Mineral County pop 4,535 across 3,459 sq mi — extremely dispersed rural population."
            ),
            "elderly_percentage": "~30%+ over 65 (median age 59.2 — very elderly community; limited mobility)",
            "mobile_homes": (
                "Significant mobile home stock in and around Superior; aging housing stock common "
                "in remote western Montana communities."
            ),
            "special_needs_facilities": (
                "Critical access hospital, volunteer fire/EMS, county courthouse. Very limited "
                "social services for such a remote and elderly population."
            ),
        },
    },

    # =========================================================================
    # 8. WEST YELLOWSTONE, MT — Park Gateway
    # =========================================================================
    "west_yellowstone_mt": {
        "center": [44.6621, -111.1041],
        "terrain_notes": (
            "West Yellowstone (pop ~1,272) is a gateway town to Yellowstone National Park, sitting "
            "at 6,660 ft elevation on the Madison Plateau in Gallatin County. The town occupies just "
            "0.80 square miles immediately adjacent to the park's west entrance, surrounded by Gallatin "
            "National Forest and Yellowstone NP on all sides. The terrain is a high-elevation plateau "
            "dominated by lodgepole pine — the same fuel type that carried the catastrophic 1988 "
            "Yellowstone fires across 793,880 acres (36% of the park). The 1988 fires are a defining "
            "event in American wildfire history: they questioned a century of fire suppression policy, "
            "demonstrated that fires can create their own weather systems, and showed that embers could "
            "be thrown a mile or more ahead of crown fire fronts. West Yellowstone itself nearly burned "
            "in September 1988 when an unexpected wind shift brought the North Fork Fire within 100 "
            "yards of structures, forcing emergency evacuations. The town holds the record for the "
            "lowest temperature ever recorded in the contiguous US (-66F) and has a subarctic climate, "
            "but summers bring extreme fire risk in the dense lodgepole forests. The town's economy "
            "is entirely tourism-dependent, with estimates of 41% Hispanic population and significant "
            "seasonal workforce housing challenges."
        ),
        "key_features": [
            {"name": "Yellowstone National Park", "bearing": "E/S", "type": "national_park",
             "notes": "West entrance directly adjacent; 2.2 million acres; 1988 fires burned 793,880 acres; lodgepole pine dominant fuel"},
            {"name": "Gallatin National Forest", "bearing": "N/W", "type": "national_forest",
             "notes": "Surrounds town on non-park sides; continuous lodgepole pine forest; fire from any direction threatens town"},
            {"name": "Madison Plateau", "bearing": "surrounding", "type": "plateau",
             "notes": "High elevation (6,660 ft) flat terrain; lodgepole pine monoculture = extreme crown fire potential"},
            {"name": "Madison River", "bearing": "W/N", "type": "river",
             "notes": "Flows northwest from park; limited firebreak value in lodgepole terrain"},
            {"name": "Hebgen Lake", "bearing": "NW", "type": "lake",
             "notes": "8 miles NW; potential refuge area but access road through forest"},
        ],
        "elevation_range_ft": [6500, 8000],
        "wui_exposure": "extreme",
        "historical_fires": [
            {"name": "North Fork Fire (1988 Yellowstone)", "year": 1988, "acres": 500000,
             "details": "Largest of the 1988 fires; human-caused; came within 100 yards of West Yellowstone structures; emergency evacuations Sept 6; wind shift nearly caused catastrophic loss; firefighters attempted bulldozer fire breaks"},
            {"name": "Yellowstone Fires Complex (1988)", "year": 1988, "acres": 793880,
             "details": "Combined acreage of all 1988 fires; 36% of park burned; high winds moved fire through tree crowns throwing embers 1+ mile ahead; 25,000 firefighters deployed; $120M suppression cost; fundamentally changed US fire policy"},
            {"name": "West Fork Fire", "year": 2024, "acres": 853,
             "details": "Burned near West Yellowstone in heavy fuel loading; steep terrain; 33% containment; demonstrated ongoing threat"},
            {"name": "Horn Fire", "year": 2024, "acres": 2000,
             "details": "17 miles NW of West Yellowstone between Cliff Lake and Highway 87; forced highway closure and evacuation warnings"},
        ],
        "evacuation_routes": [
            {"route": "US-191/US-287 North (toward Big Sky/Bozeman)", "direction": "N", "lanes": 2,
             "bottleneck": "Gallatin Canyon — narrow, winding 2-lane road through 50 miles of forest; limited passing",
             "risk": "Primary evacuation route but passes through dense forest for entire length; fire can close road; 90 miles to Bozeman"},
            {"route": "US-20 West (toward Idaho Falls)", "direction": "W", "lanes": 2,
             "bottleneck": "Targhee Pass (7,072 ft); forested mountain pass; 2-lane",
             "risk": "Crosses Continental Divide through lodgepole forest; 110 miles to Idaho Falls; fire can close pass"},
            {"route": "US-191 South (into Yellowstone NP)", "direction": "S", "lanes": 2,
             "bottleneck": "Park entrance; single road; 100+ miles to any other town via park roads",
             "risk": "NOT a viable evacuation route — leads into the park with fires, wildlife, and extremely long distances to exit"},
            {"route": "US-287 South (toward Hebgen Lake)", "direction": "S/W", "lanes": 2,
             "bottleneck": "2-lane through forest; connects to US-20 eventually",
             "risk": "Alternative to reach Idaho but through same forested terrain; earthquake-damaged Hebgen Dam area"},
        ],
        "fire_spread_characteristics": {
            "primary_wind_regime": (
                "High-elevation plateau winds with strong afternoon thermal development. The 1988 fires "
                "demonstrated that high winds (40+ mph) in this terrain produce unstoppable crown fire in "
                "lodgepole pine. Fires can create their own pyroconvective weather systems generating "
                "erratic winds. The town's flat, forested setting means fire can approach from any direction."
            ),
            "critical_corridors": [
                "Yellowstone NP west boundary — fire from park threatens town directly",
                "Gallatin Canyon corridor — continuous forest north toward Big Sky",
                "Madison Plateau — flat lodgepole terrain allows fire to run unimpeded",
                "Hebgen Lake area — fires west/northwest approach through dense timber",
            ],
            "rate_of_spread_potential": (
                "Extreme. Lodgepole pine crown fire in wind events can travel 5-10+ miles per day. "
                "The 1988 fires covered 10 miles in a single afternoon on multiple occasions. "
                "Flat terrain with continuous fuel and no natural firebreaks around West Yellowstone "
                "means any approaching crown fire can reach town without stopping."
            ),
            "spotting_distance": (
                "1-2+ miles documented in 1988 fires. High winds threw burning embers across rivers, "
                "roads, and prepared firebreaks. The North Fork Fire spotted ahead by a mile or more "
                "on multiple occasions, outpacing suppression efforts completely."
            ),
        },
        "infrastructure_vulnerabilities": {
            "water_system": (
                "Small municipal system for ~1,300 permanent residents. Summer tourism may "
                "increase water demand 5-10x. Fire hydrant system limited to town core. "
                "Surrounding forest has no water infrastructure."
            ),
            "power": (
                "Remote grid connection; single transmission line through forested corridor. "
                "Power outages during fire events isolate the community. Backup generation "
                "limited to individual businesses."
            ),
            "communications": (
                "Cell coverage in town but gaps in surrounding forest and park. Park Service "
                "radio network provides some redundancy. Emergency communications dependent on "
                "cell towers in fire-exposed locations."
            ),
            "medical": (
                "West Yellowstone Clinic — small clinic only; no hospital. Nearest hospital is "
                "in Bozeman (90 miles north through Gallatin Canyon) or Idaho Falls (110 miles west). "
                "Air evacuation limited by smoke conditions and 6,660 ft elevation (reduced helicopter "
                "performance). Medical surge capacity essentially zero."
            ),
        },
        "demographics_risk_factors": {
            "population": 1272,
            "seasonal_variation": (
                "Extreme seasonal swing. Yellowstone NP receives 4+ million visitors/year; West "
                "Yellowstone is the primary west entrance gateway. Summer population may be 5-10x "
                "permanent residents on peak days. Thousands of tourists unfamiliar with fire risk, "
                "evacuation routes, or local conditions. International visitors (significant Chinese "
                "tourism) may face language barriers during evacuation."
            ),
            "elderly_percentage": "~10% over 65 (median age 33.3 — young due to seasonal workforce; BUT seasonal elderly tourists are significant)",
            "mobile_homes": (
                "Seasonal workforce housing includes mobile homes and temporary structures. "
                "Tourism economy creates housing instability."
            ),
            "special_needs_facilities": (
                "Small clinic, hotels/motels with transient populations, campgrounds in surrounding "
                "forest, seasonal workforce housing of varying quality. No assisted living or "
                "nursing facilities."
            ),
        },
    },

}




# =============================================================================
# PNW & Northern Rockies Ignition Sources
# =============================================================================

PNW_IGNITION_SOURCES = {
    "bend_or": {
        "lat": 44.06,
        "lon": -121.31,
        "radius_km": 50,
        "primary": [
            {
                "source": "Recreation / campfire escapes",
                "risk": "HIGH",
                "detail": (
                    "Bend is the outdoor recreation capital of Central Oregon. "
                    "Deschutes National Forest sees heavy camping, mountain biking, "
                    "and off-road vehicle use. Escaped campfires and abandoned "
                    "campfire rings are the top ignition source."
                ),
            },
            {
                "source": "US-97 vehicle ignitions",
                "risk": "MODERATE",
                "detail": (
                    "Major N-S highway through dry juniper/sage. Catalytic "
                    "converters on dry grass, vehicle fires, and roadside debris "
                    "burning."
                ),
            },
            {
                "source": "Power lines (PacifiCorp)",
                "risk": "MODERATE",
                "detail": (
                    "Distribution lines through forested areas on city's west side. "
                    "Wind events can cause tree-into-line contacts in ponderosa "
                    "pine stands."
                ),
            },
            {
                "source": "Lightning",
                "risk": "MODERATE",
                "detail": (
                    "Dry thunderstorms in late summer bring lightning to Cascade "
                    "foothills. The Two Bulls Fire (2014) terrain is classic "
                    "lightning-start terrain."
                ),
            },
        ],
        "corridors": [
            {
                "name": "US-97",
                "direction": "N-S",
                "risk": "Primary corridor through high desert; vehicle ignitions",
            },
            {
                "name": "US-20 (to Sisters)",
                "direction": "NW",
                "risk": "Forest road corridor; recreation traffic",
            },
            {
                "name": "Century Drive (Cascade Lakes Hwy)",
                "direction": "W/SW",
                "risk": "Mountain recreation corridor into national forest",
            },
        ],
    },
    "medford_ashland_or": {
        "lat": 42.33,
        "lon": -122.87,
        "radius_km": 60,
        "primary": [
            {
                "source": "Human-caused (arson / homeless encampments)",
                "risk": "HIGH",
                "detail": (
                    "The Almeda Fire (2020) was human-caused, starting in a field "
                    "in N Ashland. Bear Creek greenway has history of encampment "
                    "fires. Arson and negligent human activity are the dominant "
                    "ignition source in the Bear Creek corridor."
                ),
            },
            {
                "source": "I-5 corridor vehicle ignitions",
                "risk": "HIGH",
                "detail": (
                    "I-5 runs N-S through the valley; heavy truck traffic from "
                    "California. Catalytic converters on dry grass in median and "
                    "shoulders. Vehicle fires on steep grades near Siskiyou Summit."
                ),
            },
            {
                "source": "Agricultural burning",
                "risk": "MODERATE",
                "detail": (
                    "Rogue Valley has significant agricultural operations. "
                    "Prescribed and debris burns can escape during wind events."
                ),
            },
            {
                "source": "Power lines (PacifiCorp)",
                "risk": "MODERATE",
                "detail": (
                    "Distribution and transmission lines through valley. Strong "
                    "S wind events (like the Almeda conditions) stress infrastructure."
                ),
            },
        ],
        "corridors": [
            {
                "name": "I-5",
                "direction": "N-S",
                "risk": "Primary corridor; Almeda Fire followed this valley axis",
            },
            {
                "name": "Bear Creek Greenway",
                "direction": "N-S",
                "risk": "Riparian corridor connecting communities; homeless "
                        "encampment ignition risk",
            },
            {
                "name": "OR-66 (Greensprings Hwy)",
                "direction": "E",
                "risk": "Mountain road to Klamath; fire-prone terrain",
            },
        ],
    },
    "sisters_or": {
        "lat": 44.29,
        "lon": -121.55,
        "radius_km": 40,
        "primary": [
            {
                "source": "Lightning (dry thunderstorms)",
                "risk": "HIGH",
                "detail": (
                    "Cascade crest receives significant dry lightning. B&B Complex "
                    "(2003) and Milli Fire (2017) were both lightning-caused. "
                    "10-20 fires can start from a single passing storm."
                ),
            },
            {
                "source": "Recreation / campfire escapes",
                "risk": "HIGH",
                "detail": (
                    "Heavy recreation use in Deschutes NF around Sisters. "
                    "Camp Sherman, Black Butte Ranch, and dispersed camping "
                    "areas are all high-use zones surrounded by dry forest."
                ),
            },
            {
                "source": "Power lines in forest",
                "risk": "MODERATE",
                "detail": (
                    "Distribution lines through thick ponderosa pine stands. "
                    "Tree-into-line contacts during wind events."
                ),
            },
        ],
        "corridors": [
            {
                "name": "US-20",
                "direction": "E-W",
                "risk": "Main highway through town; connects to Bend",
            },
            {
                "name": "OR-242 (McKenzie Highway)",
                "direction": "W/SW",
                "risk": "Narrow mountain road through dense forest; limited access",
            },
            {
                "name": "US-20/OR-126 to Santiam Pass",
                "direction": "NW",
                "risk": "Mountain corridor; recreation traffic and lightning zones",
            },
        ],
    },
    "la_pine_or": {
        "lat": 43.68,
        "lon": -121.50,
        "radius_km": 40,
        "primary": [
            {
                "source": "Human-caused (debris burning / equipment)",
                "risk": "HIGH",
                "detail": (
                    "Rural community with many residents on forested parcels. "
                    "Debris burning, yard maintenance equipment, and chainsaw "
                    "use in dry forest are common ignition sources. Darlene fires "
                    "threatened the area repeatedly."
                ),
            },
            {
                "source": "US-97 vehicle corridor",
                "risk": "MODERATE",
                "detail": (
                    "Major N-S highway through dense forest. Vehicle fires, "
                    "catalytic converter ignitions on dry roadside vegetation."
                ),
            },
            {
                "source": "Lightning",
                "risk": "MODERATE",
                "detail": (
                    "Dry thunderstorms affect the Newberry Volcanic area to the E. "
                    "Lightning starts in lodgepole pine are common."
                ),
            },
        ],
        "corridors": [
            {
                "name": "US-97",
                "direction": "N-S",
                "risk": "Major highway through forested community",
            },
            {
                "name": "County roads E to Newberry",
                "direction": "E/SE",
                "risk": "Forest roads; Darlene fire origins",
            },
        ],
    },
    "the_dalles_or": {
        "lat": 45.60,
        "lon": -121.18,
        "radius_km": 50,
        "primary": [
            {
                "source": "Human-caused (roadside ignitions)",
                "risk": "HIGH",
                "detail": (
                    "The 2025 Rowena Fire was human-caused. I-84 corridor fires "
                    "are frequent. Eagle Creek Fire (2017) was caused by fireworks. "
                    "Human ignitions dominate in the gorge."
                ),
            },
            {
                "source": "Railroad (BNSF / UP)",
                "risk": "HIGH",
                "detail": (
                    "Rail lines run on both sides of the Columbia River through "
                    "the gorge. Brake sparks and equipment failures in dry grass "
                    "terrain. Tunnel Fire (2023) sparked by train."
                ),
            },
            {
                "source": "I-84 vehicle ignitions",
                "risk": "MODERATE",
                "detail": (
                    "Major interstate through the gorge. Vehicle fires, tire "
                    "blowouts, and dragging equipment on dry grass shoulders."
                ),
            },
        ],
        "corridors": [
            {
                "name": "I-84",
                "direction": "E-W",
                "risk": "Primary gorge corridor; vehicle and human ignitions",
            },
            {
                "name": "BNSF / UP rail lines",
                "direction": "E-W",
                "risk": "Both sides of Columbia River; train-sparked fires",
            },
            {
                "name": "US-197",
                "direction": "S",
                "risk": "Highway S from The Dalles toward Maupin; grass terrain",
            },
        ],
    },
    "klamath_falls_or": {
        "lat": 42.22,
        "lon": -121.78,
        "radius_km": 60,
        "primary": [
            {
                "source": "Lightning (dry thunderstorms)",
                "risk": "HIGH",
                "detail": (
                    "Fremont-Winema NF receives significant dry lightning in summer. "
                    "Bootleg Fire (2021) started from lightning in heavy timber. "
                    "Remote terrain makes early detection and suppression difficult."
                ),
            },
            {
                "source": "Agricultural equipment / debris burning",
                "risk": "MODERATE",
                "detail": (
                    "Klamath Basin has extensive agricultural and ranch operations. "
                    "Equipment and burning in dry conditions."
                ),
            },
            {
                "source": "US-97 / OR-140 vehicle ignitions",
                "risk": "MODERATE",
                "detail": (
                    "Major highways through dry terrain. Vehicle and equipment fires."
                ),
            },
        ],
        "corridors": [
            {
                "name": "US-97",
                "direction": "N-S",
                "risk": "Primary N-S corridor through basin",
            },
            {
                "name": "OR-140",
                "direction": "E",
                "risk": "Road into Fremont NF; Bootleg Fire area",
            },
            {
                "name": "OR-62",
                "direction": "NW",
                "risk": "Road toward Crater Lake; forest corridor",
            },
        ],
    },
    "hood_river_or": {
        "lat": 45.71,
        "lon": -121.52,
        "radius_km": 40,
        "primary": [
            {"source": "Human-caused (recreation)", "risk": "HIGH",
             "detail": "Heavy recreation traffic; windsurfing/kiteboarding visitors. Eagle Creek 2017 was fireworks."},
            {"source": "Railroad (BNSF)", "risk": "MODERATE",
             "detail": "Rail lines along Columbia River through Gorge. Brake sparks in dry grass."},
            {"source": "I-84 vehicle ignitions", "risk": "MODERATE",
             "detail": "Major interstate through narrow Gorge corridor."},
        ],
        "corridors": [
            {"name": "I-84 / Columbia Gorge", "direction": "E-W", "risk": "Primary corridor; vehicle and human ignitions"},
            {"name": "OR-35 (Mt. Hood)", "direction": "S", "risk": "Mountain road through forest"},
        ],
    },
    "grants_pass_or": {
        "lat": 42.44,
        "lon": -123.33,
        "radius_km": 50,
        "primary": [
            {"source": "Human-caused (arson / debris burning)", "risk": "HIGH",
             "detail": "Rogue Valley has high human-caused ignition rate. Rural debris burning escapes."},
            {"source": "I-5 vehicle ignitions", "risk": "MODERATE",
             "detail": "Interstate through valley with dry grass and brush shoulders."},
            {"source": "Lightning", "risk": "MODERATE",
             "detail": "Coast Range and Siskiyou thunderstorms in summer."},
        ],
        "corridors": [
            {"name": "I-5", "direction": "N-S", "risk": "Primary valley corridor"},
            {"name": "US-199 (Illinois Valley)", "direction": "SW", "risk": "Forest road to California"},
        ],
    },
    "pendleton_or": {
        "lat": 45.67,
        "lon": -118.79,
        "radius_km": 50,
        "primary": [
            {"source": "Agricultural equipment / combines", "risk": "HIGH",
             "detail": "Wheat harvest fires from combine sparks and equipment in dry stubble."},
            {"source": "Lightning", "risk": "MODERATE",
             "detail": "Blue Mountain thunderstorms drift north into wheat country."},
            {"source": "I-84 vehicle ignitions", "risk": "MODERATE",
             "detail": "Interstate through grass and wheat terrain."},
        ],
        "corridors": [
            {"name": "I-84", "direction": "E-W", "risk": "Cabbage Hill grass fires along highway"},
            {"name": "US-395 South", "direction": "S", "risk": "Blue Mountain forest corridor"},
        ],
    },
    "john_day_or": {
        "lat": 44.42,
        "lon": -118.95,
        "radius_km": 60,
        "primary": [
            {"source": "Lightning (dry thunderstorms)", "risk": "HIGH",
             "detail": "Blue Mountains receive extensive dry lightning in summer. Canyon Creek Complex (2015) was lightning."},
            {"source": "Human-caused (recreation / campfires)", "risk": "MODERATE",
             "detail": "Backcountry camping and OHV use. Remote terrain delays detection."},
        ],
        "corridors": [
            {"name": "Canyon Creek", "direction": "S", "risk": "Drainage corridor into Blue Mountain timber"},
            {"name": "US-26", "direction": "E-W", "risk": "Mountain highway through mixed fuel"},
        ],
    },
    "roseburg_or": {
        "lat": 43.22,
        "lon": -123.34,
        "radius_km": 50,
        "primary": [
            {"source": "Human-caused (debris burning / arson)", "risk": "HIGH",
             "detail": "Rural residential areas with debris burning. History of arson-caused fires."},
            {"source": "Lightning", "risk": "MODERATE",
             "detail": "Coast Range and Cascade foothills lightning events."},
            {"source": "I-5 vehicle ignitions", "risk": "MODERATE",
             "detail": "Interstate through valley with grass and brush."},
        ],
        "corridors": [
            {"name": "I-5", "direction": "N-S", "risk": "Canyon sections with brush fires"},
            {"name": "Cow Creek / OR-227", "direction": "S", "risk": "Canyon road toward Rogue Valley"},
        ],
    },
    "sweet_home_or": {
        "lat": 44.40,
        "lon": -122.74,
        "radius_km": 40,
        "primary": [
            {"source": "Lightning", "risk": "HIGH",
             "detail": "Cascade foothills and S. Santiam canyon receive dry lightning in late summer."},
            {"source": "Human-caused (recreation / timber)", "risk": "MODERATE",
             "detail": "Green Peter/Foster reservoir recreation; timber operations."},
        ],
        "corridors": [
            {"name": "S. Santiam Canyon (US-20)", "direction": "E", "risk": "Canyon fire corridor from Cascades"},
        ],
    },
    "chelan_wa": {
        "lat": 47.84,
        "lon": -120.02,
        "radius_km": 50,
        "primary": [
            {
                "source": "Lightning (dry thunderstorms)",
                "risk": "HIGH",
                "detail": (
                    "Chelan area is one of the most lightning-struck regions in "
                    "the entire US. Dry lightning is the primary ignition source. "
                    "2015 Chelan Complex started from multiple lightning strikes "
                    "on Aug 14 in extremely dry conditions."
                ),
            },
            {
                "source": "Recreation / campfire",
                "risk": "MODERATE",
                "detail": (
                    "Lake Chelan is a major summer recreation destination. "
                    "Campfires and recreation activities in dry terrain."
                ),
            },
            {
                "source": "Power infrastructure",
                "risk": "MODERATE",
                "detail": (
                    "Distribution lines in steep terrain. Wind events cause "
                    "tree contacts in forested areas above town."
                ),
            },
        ],
        "corridors": [
            {
                "name": "US-97A",
                "direction": "S",
                "risk": "Highway along Columbia River to Wenatchee",
            },
            {
                "name": "SR-150 (Manson Highway)",
                "direction": "NW along lake",
                "risk": "Lakeside road; limited evacuation",
            },
            {
                "name": "Antoine Creek Road",
                "direction": "N",
                "risk": "Origin area of 2015 Chelan Complex; steep drainage",
            },
        ],
    },
    "wenatchee_wa": {
        "lat": 47.42,
        "lon": -120.32,
        "radius_km": 50,
        "primary": [
            {
                "source": "Arson / human-caused",
                "risk": "HIGH",
                "detail": (
                    "Sleepy Hollow Fire (2015) was deliberately set by a mentally "
                    "ill individual. Human-caused fires dominate in the foothills "
                    "WUI zone. Debris burning and homeless encampments are also "
                    "significant."
                ),
            },
            {
                "source": "Lightning",
                "risk": "MODERATE",
                "detail": (
                    "East Cascades terrain receives dry lightning. Less frequent "
                    "than Chelan but still significant in summer."
                ),
            },
            {
                "source": "Vehicle / equipment",
                "risk": "MODERATE",
                "detail": (
                    "US-2 and US-97 corridors through dry grass and sage terrain. "
                    "Agricultural equipment in orchards and dry grass."
                ),
            },
        ],
        "corridors": [
            {
                "name": "US-2",
                "direction": "E-W",
                "risk": "Major highway from Cascades to Columbia Basin",
            },
            {
                "name": "US-97",
                "direction": "N-S",
                "risk": "N to Chelan, S through dry terrain",
            },
            {
                "name": "US-97A (Columbia River)",
                "direction": "N",
                "risk": "River road; ignition risk in grass/sage margins",
            },
        ],
    },
    "leavenworth_wa": {
        "lat": 47.60,
        "lon": -120.66,
        "radius_km": 30,
        "primary": [
            {
                "source": "Lightning (dry thunderstorms)",
                "risk": "HIGH",
                "detail": (
                    "One of the most lightning-struck areas in the United States. "
                    "Not uncommon for 10-20 fires to start from a single passing "
                    "storm. Icicle Creek basin and surrounding ridges are prime "
                    "lightning-start terrain. 1994 Rat Creek Fire was lightning."
                ),
            },
            {
                "source": "Recreation / campfire",
                "risk": "MODERATE",
                "detail": (
                    "Leavenworth is a major tourist destination year-round. "
                    "Icicle Creek canyon is heavily used for camping, climbing, "
                    "and hiking. Campfire escapes in dispersed camping areas."
                ),
            },
            {
                "source": "Power lines (PUD)",
                "risk": "MODERATE",
                "detail": (
                    "Chelan PUD distribution in steep forested terrain. Tree-line "
                    "contacts during storms and wind events."
                ),
            },
        ],
        "corridors": [
            {
                "name": "US-2 (Stevens Pass)",
                "direction": "W/NW",
                "risk": "Only western evacuation route; narrow mountain highway",
            },
            {
                "name": "Icicle Creek Road",
                "direction": "SW",
                "risk": "Dead-end road into wilderness; fire pathway to town",
            },
            {
                "name": "US-2/US-97 (to Wenatchee)",
                "direction": "E",
                "risk": "Primary evacuation route; narrow river valley",
            },
        ],
    },
    "ellensburg_wa": {
        "lat": 46.99,
        "lon": -120.55,
        "radius_km": 60,
        "primary": [
            {
                "source": "Vehicle / equipment (I-90 corridor)",
                "risk": "HIGH",
                "detail": (
                    "I-90 carries massive truck traffic through the wind gap. "
                    "Dragging equipment, tire blowouts, and vehicle fires in "
                    "the bone-dry grass along the highway are the top ignition "
                    "source. Vantage Hwy Fire (2022) started during prime burning."
                ),
            },
            {
                "source": "Agricultural equipment",
                "risk": "HIGH",
                "detail": (
                    "Kittitas Valley has extensive hay, grain, and cattle ranching. "
                    "Combines, disc equipment, and mowing in dry grass during "
                    "wind events. Taylor Bridge Fire (2012) spread into timber."
                ),
            },
            {
                "source": "Power lines (PSE)",
                "risk": "MODERATE",
                "detail": (
                    "Major transmission lines cross the valley. Extreme Snoqualmie "
                    "gap winds (50-70 mph) stress conductors and poles."
                ),
            },
        ],
        "corridors": [
            {
                "name": "I-90",
                "direction": "E-W",
                "risk": "Major transcontinental route through wind gap",
            },
            {
                "name": "Vantage Highway (SR-10/I-82)",
                "direction": "E/SE",
                "risk": "2022 fire corridor; sage and grass terrain",
            },
            {
                "name": "US-97",
                "direction": "N from town",
                "risk": "Into timber country; Taylor Bridge Fire area",
            },
        ],
    },
    "boise_id": {
        "lat": 43.62,
        "lon": -116.21,
        "radius_km": 50,
        "primary": [
            {
                "source": "Fireworks / arson (human-caused, >80%)",
                "risk": "HIGH",
                "detail": (
                    "Over 80% of Treasure Valley wildfires are human-caused. "
                    "Table Rock Fire (2016) started by illegal fireworks. 8th St "
                    "Fire (1996) started by police tracer rounds. Fireworks "
                    "around July 4th are the single highest risk period."
                ),
            },
            {
                "source": "Vehicle / roadside ignitions",
                "risk": "MODERATE",
                "detail": (
                    "Highway 21, Highway 55, and I-84 all pass through foothills "
                    "grass terrain. Catalytic converters on dry grass shoulders."
                ),
            },
            {
                "source": "Power lines (Idaho Power)",
                "risk": "MODERATE",
                "detail": (
                    "Distribution lines in foothills WUI. Wind events cause "
                    "equipment failures in sage/grass terrain."
                ),
            },
            {
                "source": "Lightning",
                "risk": "MODERATE",
                "detail": (
                    "Late summer dry thunderstorms. 2009 Foothills Fire was "
                    "lightning-caused."
                ),
            },
        ],
        "corridors": [
            {
                "name": "Highway 21 (to Lucky Peak)",
                "direction": "E",
                "risk": "Oregon Trail Fire (2008) corridor; foothills grass",
            },
            {
                "name": "Highway 55 (to McCall)",
                "direction": "N",
                "risk": "Through foothills sage into mountains",
            },
            {
                "name": "I-84",
                "direction": "E-W",
                "risk": "Major interstate through S Boise; trucking ignitions",
            },
        ],
    },
    "mccall_id": {
        "lat": 44.89,
        "lon": -116.10,
        "radius_km": 40,
        "primary": [
            {
                "source": "Lightning (dry thunderstorms)",
                "risk": "HIGH",
                "detail": (
                    "Payette National Forest has extensive fire history from "
                    "lightning. Remote terrain with limited access means fires "
                    "can grow before suppression arrives. McCall smokejumper "
                    "base exists specifically because of the frequency."
                ),
            },
            {
                "source": "Recreation / campfire",
                "risk": "MODERATE",
                "detail": (
                    "Popular summer destination with camping, boating, and "
                    "backcountry recreation. Dispersed camping in dry forest."
                ),
            },
            {
                "source": "Equipment / chainsaws",
                "risk": "LOW",
                "detail": (
                    "Logging and forestry operations in surrounding NF. "
                    "Equipment ignitions in dry timber."
                ),
            },
        ],
        "corridors": [
            {
                "name": "Highway 55",
                "direction": "S (to Boise)",
                "risk": "Primary access route; forest corridor",
            },
            {
                "name": "West Mountain Road",
                "direction": "W",
                "risk": "Identified fire pathway into McCall from modeling",
            },
            {
                "name": "Warren Wagon Road",
                "direction": "N",
                "risk": "Into remote Payette NF; limited access backcountry",
            },
        ],
    },
    "missoula_mt": {
        "lat": 46.87,
        "lon": -114.00,
        "radius_km": 60,
        "primary": [
            {
                "source": "Lightning (dry thunderstorms)",
                "risk": "HIGH",
                "detail": (
                    "Montana's Northern Rockies receive extensive dry lightning "
                    "in late July through September. Lolo Peak (2017), Rice Ridge "
                    "(2017), and Canyon Creek (1988) all started from lightning. "
                    "Remote wilderness terrain limits initial attack."
                ),
            },
            {
                "source": "Human-caused (campfire, debris burning)",
                "risk": "MODERATE",
                "detail": (
                    "Heavy recreation use in surrounding national forests. "
                    "Campfire escapes, debris burning in rural areas around "
                    "Missoula. 37% of regional fires are human-caused."
                ),
            },
            {
                "source": "Railroad (Montana Rail Link / BNSF)",
                "risk": "MODERATE",
                "detail": (
                    "Rail lines follow Clark Fork River through Missoula. "
                    "Equipment sparks in dry grass along rights-of-way."
                ),
            },
        ],
        "corridors": [
            {
                "name": "I-90",
                "direction": "E-W",
                "risk": "Through city and Clark Fork valley",
            },
            {
                "name": "US-93 (Bitterroot Valley)",
                "direction": "S",
                "risk": "Primary corridor into Bitterroot fire zone",
            },
            {
                "name": "SR-200 (Clark Fork corridor)",
                "direction": "W",
                "risk": "Into Superior / fire-prone Clark Fork drainage",
            },
            {
                "name": "Rattlesnake Drive",
                "direction": "N",
                "risk": "Into Rattlesnake Wilderness; limited access",
            },
        ],
    },
    "helena_mt": {
        "lat": 46.59,
        "lon": -112.04,
        "radius_km": 50,
        "primary": [
            {
                "source": "Human-caused (debris burning, equipment)",
                "risk": "HIGH",
                "detail": (
                    "Horse Gulch Fire (2024) was human-caused. Rural properties "
                    "around Helena in forested areas generate debris burning "
                    "and equipment ignitions. Mann Gulch Fire (1949) was also "
                    "likely human-caused from nearby ranch."
                ),
            },
            {
                "source": "Lightning",
                "risk": "HIGH",
                "detail": (
                    "Helena National Forest and surrounding mountains receive "
                    "significant dry lightning. Big Belt Mountains and Elkhorn "
                    "Mountains are prime lightning country."
                ),
            },
            {
                "source": "I-15 corridor vehicles",
                "risk": "MODERATE",
                "detail": (
                    "Major N-S interstate through mountain terrain. Vehicle "
                    "fires and roadside ignitions."
                ),
            },
        ],
        "corridors": [
            {
                "name": "I-15",
                "direction": "N-S",
                "risk": "Primary N-S corridor through Helena valley",
            },
            {
                "name": "US-12 (to Townsend)",
                "direction": "E",
                "risk": "Canyon road toward Big Belt Mountains; Horse Gulch area",
            },
            {
                "name": "Lincoln Road (SR-200)",
                "direction": "W/NW",
                "risk": "Into forested mountains; recreation and dispersed camping",
            },
        ],
    },
    "kalispell_whitefish_mt": {
        "lat": 48.30,
        "lon": -114.26,
        "radius_km": 60,
        "primary": [
            {
                "source": "Lightning (dominant ignition source, 62%)",
                "risk": "HIGH",
                "detail": (
                    "62% of wildfire starts on Flathead NF are lightning-caused. "
                    "Late summer dry thunderstorms produce numerous starts in "
                    "remote, hard-to-access terrain. Mixed to high severity fire "
                    "regime means large, stand-replacing fires."
                ),
            },
            {
                "source": "Human-caused (37% of starts)",
                "risk": "HIGH",
                "detail": (
                    "37% of Flathead NF fires are human-caused. Heavy recreation "
                    "use (Glacier NP visitors), campfires, and debris burning. "
                    "Population growth increasing WUI interactions."
                ),
            },
            {
                "source": "Power infrastructure",
                "risk": "MODERATE",
                "detail": (
                    "Distribution and transmission lines through forested areas. "
                    "Wind events and tree contacts in dense timber."
                ),
            },
        ],
        "corridors": [
            {
                "name": "US-93",
                "direction": "N-S",
                "risk": "Primary highway through Flathead Valley to Glacier",
            },
            {
                "name": "US-2 (to Glacier NP)",
                "direction": "E",
                "risk": "Corridor toward Glacier; dense forest on both sides",
            },
            {
                "name": "SR-40 / North Fork Road",
                "direction": "N/NW",
                "risk": "Remote road toward Glacier; Hallowat Fire area",
            },
        ],
    },
}


# =============================================================================
# PNW & Northern Rockies Station Climatology
# =============================================================================
# Fire season months (June-October) with monthly data for ASOS stations
# nearest to each profiled city. Based on historical ASOS records (1990-2025).
# Sources: WRCC, xmACIS2, IEM, Weather Spark, NWS local climate pages.
#
# Note: PNW fire weather is fundamentally different from Great Plains fire
# weather. Key differences:
#   - Lower absolute wind speeds but terrain-channeled winds create local maxima
#   - Fire season is Jul-Oct (vs year-round in TX/OK)
#   - RH drops to 8-15% on critical days (vs 3-8% in Great Plains)
#   - Drier dewpoints at elevation stations (Bend, La Pine, McCall)
#   - Gorge/gap winds (The Dalles, Ellensburg) rival Great Plains gusts

PNW_CLIMATOLOGY = {
    "KBDN": {
        "name": "Bend, OR (Bend Municipal Airport AWOS)",
        "elevation_ft": 3460,
        "region": "Central Oregon High Desert",
        "months": {
            6: {"normal_high_f": 76, "normal_low_f": 40, "rh_typical_min": 15, "rh_extreme_min": 6, "rh_low_days_per_month": 5, "dp_typical_low_f": 22, "dp_extreme_low_f": 5, "gust_typical_max_kt": 25, "gust_extreme_kt": 42, "gust_sig_threshold_kt": 30},
            7: {"normal_high_f": 84, "normal_low_f": 44, "rh_typical_min": 10, "rh_extreme_min": 4, "rh_low_days_per_month": 10, "dp_typical_low_f": 18, "dp_extreme_low_f": 0, "gust_typical_max_kt": 25, "gust_extreme_kt": 40, "gust_sig_threshold_kt": 30},
            8: {"normal_high_f": 83, "normal_low_f": 43, "rh_typical_min": 10, "rh_extreme_min": 4, "rh_low_days_per_month": 12, "dp_typical_low_f": 18, "dp_extreme_low_f": 0, "gust_typical_max_kt": 25, "gust_extreme_kt": 40, "gust_sig_threshold_kt": 30},
            9: {"normal_high_f": 75, "normal_low_f": 36, "rh_typical_min": 12, "rh_extreme_min": 5, "rh_low_days_per_month": 8, "dp_typical_low_f": 20, "dp_extreme_low_f": 2, "gust_typical_max_kt": 25, "gust_extreme_kt": 40, "gust_sig_threshold_kt": 30},
            10: {"normal_high_f": 61, "normal_low_f": 28, "rh_typical_min": 18, "rh_extreme_min": 8, "rh_low_days_per_month": 4, "dp_typical_low_f": 18, "dp_extreme_low_f": 2, "gust_typical_max_kt": 28, "gust_extreme_kt": 42, "gust_sig_threshold_kt": 32},
        },
    },
    "KRDM": {
        "name": "Redmond, OR (Roberts Field) -- nearest ASOS for Sisters/La Pine",
        "elevation_ft": 3081,
        "region": "Central Oregon",
        "months": {
            6: {"normal_high_f": 77, "normal_low_f": 41, "rh_typical_min": 14, "rh_extreme_min": 5, "rh_low_days_per_month": 6, "dp_typical_low_f": 22, "dp_extreme_low_f": 5, "gust_typical_max_kt": 26, "gust_extreme_kt": 44, "gust_sig_threshold_kt": 32},
            7: {"normal_high_f": 86, "normal_low_f": 45, "rh_typical_min": 9, "rh_extreme_min": 3, "rh_low_days_per_month": 12, "dp_typical_low_f": 18, "dp_extreme_low_f": -2, "gust_typical_max_kt": 26, "gust_extreme_kt": 42, "gust_sig_threshold_kt": 32},
            8: {"normal_high_f": 85, "normal_low_f": 44, "rh_typical_min": 9, "rh_extreme_min": 3, "rh_low_days_per_month": 14, "dp_typical_low_f": 18, "dp_extreme_low_f": -2, "gust_typical_max_kt": 25, "gust_extreme_kt": 40, "gust_sig_threshold_kt": 30},
            9: {"normal_high_f": 76, "normal_low_f": 36, "rh_typical_min": 12, "rh_extreme_min": 5, "rh_low_days_per_month": 8, "dp_typical_low_f": 20, "dp_extreme_low_f": 2, "gust_typical_max_kt": 26, "gust_extreme_kt": 42, "gust_sig_threshold_kt": 32},
            10: {"normal_high_f": 62, "normal_low_f": 28, "rh_typical_min": 16, "rh_extreme_min": 7, "rh_low_days_per_month": 4, "dp_typical_low_f": 18, "dp_extreme_low_f": 2, "gust_typical_max_kt": 28, "gust_extreme_kt": 44, "gust_sig_threshold_kt": 34},
        },
    },
    "KMFR": {
        "name": "Medford, OR (Rogue Valley Intl-Medford)",
        "elevation_ft": 1335,
        "region": "Southern Oregon Rogue Valley",
        "months": {
            6: {"normal_high_f": 82, "normal_low_f": 50, "rh_typical_min": 16, "rh_extreme_min": 6, "rh_low_days_per_month": 5, "dp_typical_low_f": 32, "dp_extreme_low_f": 15, "gust_typical_max_kt": 22, "gust_extreme_kt": 38, "gust_sig_threshold_kt": 28},
            7: {"normal_high_f": 92, "normal_low_f": 56, "rh_typical_min": 10, "rh_extreme_min": 4, "rh_low_days_per_month": 12, "dp_typical_low_f": 28, "dp_extreme_low_f": 10, "gust_typical_max_kt": 22, "gust_extreme_kt": 36, "gust_sig_threshold_kt": 28},
            8: {"normal_high_f": 92, "normal_low_f": 55, "rh_typical_min": 10, "rh_extreme_min": 4, "rh_low_days_per_month": 14, "dp_typical_low_f": 28, "dp_extreme_low_f": 10, "gust_typical_max_kt": 22, "gust_extreme_kt": 36, "gust_sig_threshold_kt": 28},
            9: {"normal_high_f": 83, "normal_low_f": 47, "rh_typical_min": 12, "rh_extreme_min": 5, "rh_low_days_per_month": 8, "dp_typical_low_f": 28, "dp_extreme_low_f": 12, "gust_typical_max_kt": 22, "gust_extreme_kt": 38, "gust_sig_threshold_kt": 28},
            10: {"normal_high_f": 67, "normal_low_f": 37, "rh_typical_min": 18, "rh_extreme_min": 8, "rh_low_days_per_month": 3, "dp_typical_low_f": 26, "dp_extreme_low_f": 8, "gust_typical_max_kt": 24, "gust_extreme_kt": 40, "gust_sig_threshold_kt": 30},
        },
    },
    "KLMT": {
        "name": "Klamath Falls, OR (Crater Lake-Klamath Regional)",
        "elevation_ft": 4091,
        "region": "Southern Oregon Basin",
        "months": {
            6: {"normal_high_f": 76, "normal_low_f": 40, "rh_typical_min": 14, "rh_extreme_min": 5, "rh_low_days_per_month": 6, "dp_typical_low_f": 20, "dp_extreme_low_f": 2, "gust_typical_max_kt": 24, "gust_extreme_kt": 40, "gust_sig_threshold_kt": 30},
            7: {"normal_high_f": 85, "normal_low_f": 45, "rh_typical_min": 9, "rh_extreme_min": 3, "rh_low_days_per_month": 12, "dp_typical_low_f": 16, "dp_extreme_low_f": -2, "gust_typical_max_kt": 24, "gust_extreme_kt": 38, "gust_sig_threshold_kt": 28},
            8: {"normal_high_f": 84, "normal_low_f": 43, "rh_typical_min": 8, "rh_extreme_min": 3, "rh_low_days_per_month": 15, "dp_typical_low_f": 16, "dp_extreme_low_f": -2, "gust_typical_max_kt": 22, "gust_extreme_kt": 38, "gust_sig_threshold_kt": 28},
            9: {"normal_high_f": 76, "normal_low_f": 36, "rh_typical_min": 12, "rh_extreme_min": 5, "rh_low_days_per_month": 8, "dp_typical_low_f": 18, "dp_extreme_low_f": 0, "gust_typical_max_kt": 24, "gust_extreme_kt": 40, "gust_sig_threshold_kt": 30},
            10: {"normal_high_f": 62, "normal_low_f": 28, "rh_typical_min": 18, "rh_extreme_min": 8, "rh_low_days_per_month": 3, "dp_typical_low_f": 18, "dp_extreme_low_f": 2, "gust_typical_max_kt": 26, "gust_extreme_kt": 42, "gust_sig_threshold_kt": 32},
        },
    },
    "KDLS": {
        "name": "The Dalles, OR (Columbia Gorge Regional)",
        "elevation_ft": 247,
        "region": "Columbia River Gorge",
        "months": {
            6: {"normal_high_f": 79, "normal_low_f": 52, "rh_typical_min": 18, "rh_extreme_min": 8, "rh_low_days_per_month": 4, "dp_typical_low_f": 35, "dp_extreme_low_f": 18, "gust_typical_max_kt": 32, "gust_extreme_kt": 52, "gust_sig_threshold_kt": 38},
            7: {"normal_high_f": 88, "normal_low_f": 58, "rh_typical_min": 12, "rh_extreme_min": 5, "rh_low_days_per_month": 8, "dp_typical_low_f": 30, "dp_extreme_low_f": 12, "gust_typical_max_kt": 32, "gust_extreme_kt": 52, "gust_sig_threshold_kt": 38},
            8: {"normal_high_f": 87, "normal_low_f": 57, "rh_typical_min": 12, "rh_extreme_min": 5, "rh_low_days_per_month": 10, "dp_typical_low_f": 30, "dp_extreme_low_f": 12, "gust_typical_max_kt": 30, "gust_extreme_kt": 50, "gust_sig_threshold_kt": 36},
            9: {"normal_high_f": 78, "normal_low_f": 49, "rh_typical_min": 16, "rh_extreme_min": 7, "rh_low_days_per_month": 5, "dp_typical_low_f": 30, "dp_extreme_low_f": 14, "gust_typical_max_kt": 32, "gust_extreme_kt": 52, "gust_sig_threshold_kt": 38},
            10: {"normal_high_f": 63, "normal_low_f": 41, "rh_typical_min": 22, "rh_extreme_min": 10, "rh_low_days_per_month": 2, "dp_typical_low_f": 28, "dp_extreme_low_f": 10, "gust_typical_max_kt": 34, "gust_extreme_kt": 55, "gust_sig_threshold_kt": 40},
        },
    },
    "KPDT": {
        "name": "Pendleton, OR (Eastern Oregon Regional)",
        "elevation_ft": 1496,
        "region": "NE Oregon / Columbia Plateau",
        "months": {
            6: {"normal_high_f": 80, "normal_low_f": 52, "rh_typical_min": 16, "rh_extreme_min": 6, "rh_low_days_per_month": 5, "dp_typical_low_f": 32, "dp_extreme_low_f": 15, "gust_typical_max_kt": 28, "gust_extreme_kt": 46, "gust_sig_threshold_kt": 34},
            7: {"normal_high_f": 90, "normal_low_f": 58, "rh_typical_min": 10, "rh_extreme_min": 4, "rh_low_days_per_month": 10, "dp_typical_low_f": 28, "dp_extreme_low_f": 8, "gust_typical_max_kt": 26, "gust_extreme_kt": 42, "gust_sig_threshold_kt": 32},
            8: {"normal_high_f": 89, "normal_low_f": 57, "rh_typical_min": 10, "rh_extreme_min": 4, "rh_low_days_per_month": 12, "dp_typical_low_f": 28, "dp_extreme_low_f": 8, "gust_typical_max_kt": 25, "gust_extreme_kt": 40, "gust_sig_threshold_kt": 30},
            9: {"normal_high_f": 78, "normal_low_f": 48, "rh_typical_min": 14, "rh_extreme_min": 6, "rh_low_days_per_month": 6, "dp_typical_low_f": 28, "dp_extreme_low_f": 10, "gust_typical_max_kt": 28, "gust_extreme_kt": 44, "gust_sig_threshold_kt": 34},
            10: {"normal_high_f": 63, "normal_low_f": 39, "rh_typical_min": 22, "rh_extreme_min": 10, "rh_low_days_per_month": 2, "dp_typical_low_f": 26, "dp_extreme_low_f": 8, "gust_typical_max_kt": 30, "gust_extreme_kt": 48, "gust_sig_threshold_kt": 36},
        },
    },
    "KLGD": {
        "name": "La Grande, OR (Union County)",
        "elevation_ft": 2717,
        "region": "NE Oregon / Grande Ronde Valley",
        "months": {
            6: {"normal_high_f": 76, "normal_low_f": 45, "rh_typical_min": 16, "rh_extreme_min": 7, "rh_low_days_per_month": 4, "dp_typical_low_f": 28, "dp_extreme_low_f": 12, "gust_typical_max_kt": 24, "gust_extreme_kt": 38, "gust_sig_threshold_kt": 28},
            7: {"normal_high_f": 86, "normal_low_f": 50, "rh_typical_min": 10, "rh_extreme_min": 4, "rh_low_days_per_month": 10, "dp_typical_low_f": 24, "dp_extreme_low_f": 5, "gust_typical_max_kt": 22, "gust_extreme_kt": 36, "gust_sig_threshold_kt": 26},
            8: {"normal_high_f": 85, "normal_low_f": 49, "rh_typical_min": 10, "rh_extreme_min": 4, "rh_low_days_per_month": 12, "dp_typical_low_f": 24, "dp_extreme_low_f": 5, "gust_typical_max_kt": 22, "gust_extreme_kt": 35, "gust_sig_threshold_kt": 26},
            9: {"normal_high_f": 75, "normal_low_f": 41, "rh_typical_min": 14, "rh_extreme_min": 6, "rh_low_days_per_month": 6, "dp_typical_low_f": 25, "dp_extreme_low_f": 8, "gust_typical_max_kt": 24, "gust_extreme_kt": 38, "gust_sig_threshold_kt": 28},
            10: {"normal_high_f": 60, "normal_low_f": 32, "rh_typical_min": 20, "rh_extreme_min": 10, "rh_low_days_per_month": 2, "dp_typical_low_f": 22, "dp_extreme_low_f": 5, "gust_typical_max_kt": 26, "gust_extreme_kt": 40, "gust_sig_threshold_kt": 30},
        },
    },
    "KBKE": {
        "name": "Baker City, OR (Baker City Municipal)",
        "elevation_ft": 3373,
        "region": "NE Oregon / Elkhorn Mountains",
        "months": {
            6: {"normal_high_f": 75, "normal_low_f": 43, "rh_typical_min": 15, "rh_extreme_min": 6, "rh_low_days_per_month": 5, "dp_typical_low_f": 26, "dp_extreme_low_f": 10, "gust_typical_max_kt": 24, "gust_extreme_kt": 38, "gust_sig_threshold_kt": 28},
            7: {"normal_high_f": 85, "normal_low_f": 48, "rh_typical_min": 9, "rh_extreme_min": 3, "rh_low_days_per_month": 12, "dp_typical_low_f": 22, "dp_extreme_low_f": 2, "gust_typical_max_kt": 22, "gust_extreme_kt": 36, "gust_sig_threshold_kt": 26},
            8: {"normal_high_f": 84, "normal_low_f": 46, "rh_typical_min": 9, "rh_extreme_min": 3, "rh_low_days_per_month": 14, "dp_typical_low_f": 22, "dp_extreme_low_f": 2, "gust_typical_max_kt": 22, "gust_extreme_kt": 35, "gust_sig_threshold_kt": 26},
            9: {"normal_high_f": 74, "normal_low_f": 38, "rh_typical_min": 13, "rh_extreme_min": 5, "rh_low_days_per_month": 7, "dp_typical_low_f": 24, "dp_extreme_low_f": 5, "gust_typical_max_kt": 24, "gust_extreme_kt": 38, "gust_sig_threshold_kt": 28},
            10: {"normal_high_f": 59, "normal_low_f": 29, "rh_typical_min": 18, "rh_extreme_min": 8, "rh_low_days_per_month": 3, "dp_typical_low_f": 20, "dp_extreme_low_f": 2, "gust_typical_max_kt": 26, "gust_extreme_kt": 40, "gust_sig_threshold_kt": 30},
        },
    },
    "KLKV": {
        "name": "Lakeview, OR (Lake County Airport)",
        "elevation_ft": 4733,
        "region": "SE Oregon High Desert",
        "months": {
            6: {"normal_high_f": 73, "normal_low_f": 38, "rh_typical_min": 12, "rh_extreme_min": 4, "rh_low_days_per_month": 6, "dp_typical_low_f": 18, "dp_extreme_low_f": 0, "gust_typical_max_kt": 26, "gust_extreme_kt": 42, "gust_sig_threshold_kt": 32},
            7: {"normal_high_f": 83, "normal_low_f": 42, "rh_typical_min": 8, "rh_extreme_min": 3, "rh_low_days_per_month": 14, "dp_typical_low_f": 14, "dp_extreme_low_f": -4, "gust_typical_max_kt": 24, "gust_extreme_kt": 40, "gust_sig_threshold_kt": 30},
            8: {"normal_high_f": 82, "normal_low_f": 41, "rh_typical_min": 8, "rh_extreme_min": 3, "rh_low_days_per_month": 16, "dp_typical_low_f": 14, "dp_extreme_low_f": -4, "gust_typical_max_kt": 22, "gust_extreme_kt": 38, "gust_sig_threshold_kt": 28},
            9: {"normal_high_f": 74, "normal_low_f": 34, "rh_typical_min": 11, "rh_extreme_min": 4, "rh_low_days_per_month": 8, "dp_typical_low_f": 16, "dp_extreme_low_f": -2, "gust_typical_max_kt": 24, "gust_extreme_kt": 40, "gust_sig_threshold_kt": 30},
            10: {"normal_high_f": 60, "normal_low_f": 26, "rh_typical_min": 16, "rh_extreme_min": 7, "rh_low_days_per_month": 3, "dp_typical_low_f": 16, "dp_extreme_low_f": 0, "gust_typical_max_kt": 26, "gust_extreme_kt": 42, "gust_sig_threshold_kt": 32},
        },
    },
    "KEAT": {
        "name": "Wenatchee, WA (Pangborn Memorial) -- also serves Chelan",
        "elevation_ft": 1249,
        "region": "Central Washington East Cascades",
        "months": {
            6: {"normal_high_f": 79, "normal_low_f": 52, "rh_typical_min": 16, "rh_extreme_min": 6, "rh_low_days_per_month": 5, "dp_typical_low_f": 32, "dp_extreme_low_f": 14, "gust_typical_max_kt": 26, "gust_extreme_kt": 42, "gust_sig_threshold_kt": 32},
            7: {"normal_high_f": 89, "normal_low_f": 58, "rh_typical_min": 10, "rh_extreme_min": 4, "rh_low_days_per_month": 10, "dp_typical_low_f": 28, "dp_extreme_low_f": 8, "gust_typical_max_kt": 25, "gust_extreme_kt": 40, "gust_sig_threshold_kt": 30},
            8: {"normal_high_f": 88, "normal_low_f": 57, "rh_typical_min": 10, "rh_extreme_min": 4, "rh_low_days_per_month": 12, "dp_typical_low_f": 28, "dp_extreme_low_f": 8, "gust_typical_max_kt": 24, "gust_extreme_kt": 38, "gust_sig_threshold_kt": 28},
            9: {"normal_high_f": 77, "normal_low_f": 48, "rh_typical_min": 14, "rh_extreme_min": 6, "rh_low_days_per_month": 6, "dp_typical_low_f": 28, "dp_extreme_low_f": 10, "gust_typical_max_kt": 26, "gust_extreme_kt": 42, "gust_sig_threshold_kt": 32},
            10: {"normal_high_f": 61, "normal_low_f": 38, "rh_typical_min": 20, "rh_extreme_min": 10, "rh_low_days_per_month": 2, "dp_typical_low_f": 26, "dp_extreme_low_f": 8, "gust_typical_max_kt": 28, "gust_extreme_kt": 44, "gust_sig_threshold_kt": 34},
        },
    },
    "KELN": {
        "name": "Ellensburg, WA (Bowers Field)",
        "elevation_ft": 1764,
        "region": "Kittitas Valley / Snoqualmie Gap Wind Zone",
        "months": {
            6: {"normal_high_f": 77, "normal_low_f": 47, "rh_typical_min": 16, "rh_extreme_min": 6, "rh_low_days_per_month": 5, "dp_typical_low_f": 30, "dp_extreme_low_f": 12, "gust_typical_max_kt": 35, "gust_extreme_kt": 58, "gust_sig_threshold_kt": 42},
            7: {"normal_high_f": 86, "normal_low_f": 52, "rh_typical_min": 10, "rh_extreme_min": 4, "rh_low_days_per_month": 10, "dp_typical_low_f": 26, "dp_extreme_low_f": 6, "gust_typical_max_kt": 35, "gust_extreme_kt": 56, "gust_sig_threshold_kt": 42},
            8: {"normal_high_f": 85, "normal_low_f": 51, "rh_typical_min": 10, "rh_extreme_min": 4, "rh_low_days_per_month": 12, "dp_typical_low_f": 26, "dp_extreme_low_f": 6, "gust_typical_max_kt": 34, "gust_extreme_kt": 55, "gust_sig_threshold_kt": 40},
            9: {"normal_high_f": 76, "normal_low_f": 43, "rh_typical_min": 14, "rh_extreme_min": 6, "rh_low_days_per_month": 5, "dp_typical_low_f": 28, "dp_extreme_low_f": 8, "gust_typical_max_kt": 36, "gust_extreme_kt": 60, "gust_sig_threshold_kt": 44},
            10: {"normal_high_f": 61, "normal_low_f": 34, "rh_typical_min": 22, "rh_extreme_min": 10, "rh_low_days_per_month": 2, "dp_typical_low_f": 24, "dp_extreme_low_f": 5, "gust_typical_max_kt": 38, "gust_extreme_kt": 62, "gust_sig_threshold_kt": 46},
        },
    },
    "KBOI": {
        "name": "Boise, ID (Boise Air Terminal / Gowen Field)",
        "elevation_ft": 2872,
        "region": "Treasure Valley / Boise Foothills",
        "months": {
            6: {"normal_high_f": 82, "normal_low_f": 52, "rh_typical_min": 14, "rh_extreme_min": 5, "rh_low_days_per_month": 6, "dp_typical_low_f": 28, "dp_extreme_low_f": 10, "gust_typical_max_kt": 28, "gust_extreme_kt": 45, "gust_sig_threshold_kt": 34},
            7: {"normal_high_f": 93, "normal_low_f": 60, "rh_typical_min": 8, "rh_extreme_min": 3, "rh_low_days_per_month": 14, "dp_typical_low_f": 22, "dp_extreme_low_f": 5, "gust_typical_max_kt": 26, "gust_extreme_kt": 42, "gust_sig_threshold_kt": 32},
            8: {"normal_high_f": 91, "normal_low_f": 58, "rh_typical_min": 8, "rh_extreme_min": 3, "rh_low_days_per_month": 15, "dp_typical_low_f": 22, "dp_extreme_low_f": 5, "gust_typical_max_kt": 25, "gust_extreme_kt": 40, "gust_sig_threshold_kt": 30},
            9: {"normal_high_f": 79, "normal_low_f": 48, "rh_typical_min": 12, "rh_extreme_min": 4, "rh_low_days_per_month": 6, "dp_typical_low_f": 24, "dp_extreme_low_f": 6, "gust_typical_max_kt": 28, "gust_extreme_kt": 44, "gust_sig_threshold_kt": 34},
            10: {"normal_high_f": 63, "normal_low_f": 36, "rh_typical_min": 18, "rh_extreme_min": 8, "rh_low_days_per_month": 3, "dp_typical_low_f": 22, "dp_extreme_low_f": 4, "gust_typical_max_kt": 30, "gust_extreme_kt": 48, "gust_sig_threshold_kt": 36},
        },
    },
    "KMYL": {
        "name": "McCall, ID (McCall Municipal)",
        "elevation_ft": 5024,
        "region": "Central Idaho Mountains",
        "months": {
            6: {"normal_high_f": 70, "normal_low_f": 36, "rh_typical_min": 16, "rh_extreme_min": 6, "rh_low_days_per_month": 5, "dp_typical_low_f": 20, "dp_extreme_low_f": 2, "gust_typical_max_kt": 22, "gust_extreme_kt": 36, "gust_sig_threshold_kt": 26},
            7: {"normal_high_f": 82, "normal_low_f": 40, "rh_typical_min": 9, "rh_extreme_min": 3, "rh_low_days_per_month": 12, "dp_typical_low_f": 16, "dp_extreme_low_f": -2, "gust_typical_max_kt": 22, "gust_extreme_kt": 36, "gust_sig_threshold_kt": 26},
            8: {"normal_high_f": 81, "normal_low_f": 38, "rh_typical_min": 8, "rh_extreme_min": 3, "rh_low_days_per_month": 14, "dp_typical_low_f": 16, "dp_extreme_low_f": -2, "gust_typical_max_kt": 20, "gust_extreme_kt": 34, "gust_sig_threshold_kt": 24},
            9: {"normal_high_f": 72, "normal_low_f": 32, "rh_typical_min": 12, "rh_extreme_min": 5, "rh_low_days_per_month": 6, "dp_typical_low_f": 18, "dp_extreme_low_f": 0, "gust_typical_max_kt": 22, "gust_extreme_kt": 36, "gust_sig_threshold_kt": 26},
            10: {"normal_high_f": 57, "normal_low_f": 25, "rh_typical_min": 20, "rh_extreme_min": 10, "rh_low_days_per_month": 2, "dp_typical_low_f": 16, "dp_extreme_low_f": 0, "gust_typical_max_kt": 24, "gust_extreme_kt": 38, "gust_sig_threshold_kt": 28},
        },
    },
    "KMSO": {
        "name": "Missoula, MT (Missoula International)",
        "elevation_ft": 3195,
        "region": "Western Montana Five Valleys",
        "months": {
            6: {"normal_high_f": 73, "normal_low_f": 44, "rh_typical_min": 18, "rh_extreme_min": 8, "rh_low_days_per_month": 3, "dp_typical_low_f": 28, "dp_extreme_low_f": 12, "gust_typical_max_kt": 28, "gust_extreme_kt": 44, "gust_sig_threshold_kt": 34},
            7: {"normal_high_f": 84, "normal_low_f": 49, "rh_typical_min": 10, "rh_extreme_min": 4, "rh_low_days_per_month": 10, "dp_typical_low_f": 24, "dp_extreme_low_f": 6, "gust_typical_max_kt": 26, "gust_extreme_kt": 42, "gust_sig_threshold_kt": 32},
            8: {"normal_high_f": 84, "normal_low_f": 48, "rh_typical_min": 10, "rh_extreme_min": 4, "rh_low_days_per_month": 12, "dp_typical_low_f": 24, "dp_extreme_low_f": 5, "gust_typical_max_kt": 25, "gust_extreme_kt": 40, "gust_sig_threshold_kt": 30},
            9: {"normal_high_f": 72, "normal_low_f": 39, "rh_typical_min": 14, "rh_extreme_min": 6, "rh_low_days_per_month": 5, "dp_typical_low_f": 24, "dp_extreme_low_f": 6, "gust_typical_max_kt": 28, "gust_extreme_kt": 44, "gust_sig_threshold_kt": 34},
            10: {"normal_high_f": 56, "normal_low_f": 31, "rh_typical_min": 22, "rh_extreme_min": 10, "rh_low_days_per_month": 2, "dp_typical_low_f": 22, "dp_extreme_low_f": 4, "gust_typical_max_kt": 30, "gust_extreme_kt": 48, "gust_sig_threshold_kt": 36},
        },
    },
    "KHLN": {
        "name": "Helena, MT (Helena Regional)",
        "elevation_ft": 3877,
        "region": "Central Montana Mountain Valley",
        "months": {
            6: {"normal_high_f": 73, "normal_low_f": 44, "rh_typical_min": 16, "rh_extreme_min": 6, "rh_low_days_per_month": 4, "dp_typical_low_f": 26, "dp_extreme_low_f": 8, "gust_typical_max_kt": 30, "gust_extreme_kt": 48, "gust_sig_threshold_kt": 36},
            7: {"normal_high_f": 84, "normal_low_f": 50, "rh_typical_min": 10, "rh_extreme_min": 4, "rh_low_days_per_month": 10, "dp_typical_low_f": 22, "dp_extreme_low_f": 4, "gust_typical_max_kt": 28, "gust_extreme_kt": 44, "gust_sig_threshold_kt": 34},
            8: {"normal_high_f": 84, "normal_low_f": 49, "rh_typical_min": 10, "rh_extreme_min": 3, "rh_low_days_per_month": 12, "dp_typical_low_f": 22, "dp_extreme_low_f": 3, "gust_typical_max_kt": 26, "gust_extreme_kt": 42, "gust_sig_threshold_kt": 32},
            9: {"normal_high_f": 72, "normal_low_f": 40, "rh_typical_min": 14, "rh_extreme_min": 5, "rh_low_days_per_month": 5, "dp_typical_low_f": 24, "dp_extreme_low_f": 5, "gust_typical_max_kt": 30, "gust_extreme_kt": 48, "gust_sig_threshold_kt": 36},
            10: {"normal_high_f": 57, "normal_low_f": 30, "rh_typical_min": 20, "rh_extreme_min": 10, "rh_low_days_per_month": 2, "dp_typical_low_f": 20, "dp_extreme_low_f": 2, "gust_typical_max_kt": 32, "gust_extreme_kt": 52, "gust_sig_threshold_kt": 38},
        },
    },
    "KGPI": {
        "name": "Kalispell, MT (Glacier Park Intl)",
        "elevation_ft": 2977,
        "region": "Northwest Montana Flathead Valley",
        "months": {
            6: {"normal_high_f": 72, "normal_low_f": 43, "rh_typical_min": 20, "rh_extreme_min": 8, "rh_low_days_per_month": 2, "dp_typical_low_f": 30, "dp_extreme_low_f": 14, "gust_typical_max_kt": 26, "gust_extreme_kt": 42, "gust_sig_threshold_kt": 32},
            7: {"normal_high_f": 82, "normal_low_f": 48, "rh_typical_min": 12, "rh_extreme_min": 4, "rh_low_days_per_month": 8, "dp_typical_low_f": 26, "dp_extreme_low_f": 8, "gust_typical_max_kt": 24, "gust_extreme_kt": 40, "gust_sig_threshold_kt": 30},
            8: {"normal_high_f": 82, "normal_low_f": 47, "rh_typical_min": 12, "rh_extreme_min": 4, "rh_low_days_per_month": 10, "dp_typical_low_f": 26, "dp_extreme_low_f": 8, "gust_typical_max_kt": 22, "gust_extreme_kt": 38, "gust_sig_threshold_kt": 28},
            9: {"normal_high_f": 70, "normal_low_f": 38, "rh_typical_min": 16, "rh_extreme_min": 6, "rh_low_days_per_month": 4, "dp_typical_low_f": 26, "dp_extreme_low_f": 8, "gust_typical_max_kt": 26, "gust_extreme_kt": 42, "gust_sig_threshold_kt": 32},
            10: {"normal_high_f": 55, "normal_low_f": 30, "rh_typical_min": 24, "rh_extreme_min": 12, "rh_low_days_per_month": 1, "dp_typical_low_f": 24, "dp_extreme_low_f": 6, "gust_typical_max_kt": 28, "gust_extreme_kt": 46, "gust_sig_threshold_kt": 34},
        },
    },
}


# =============================================================================
# Station-to-city mapping for quick lookups
# =============================================================================

PNW_STATION_CITY_MAP = {
    # Oregon — new WFO swarm cities
    "baker_city_or": "KBKE",
    "bly_or": "KLMT",
    "bonanza_or": "KLMT",
    "canyon_city_or": "KRDM",  # nearest ASOS
    "chiloquin_or": "KLMT",
    "cottage_grove_or": "KEUG",
    "drain_or": "KEUG",
    "dufur_or": "KDLS",
    "enterprise_or": "KLGD",
    "florence_or": "KEUG",
    "grass_valley_or": "KDLS",
    "grants_pass_or": "KMFR",
    "hood_river_or": "KDLS",
    "jacksonville_or": "KMFR",
    "john_day_or": "KRDM",  # nearest ASOS
    "joseph_or": "KLGD",
    "la_grande_or": "KLGD",
    "lakeview_or": "KLKV",
    "maupin_or": "KDLS",
    "mckenzie_bridge_or": "KEUG",
    "mosier_or": "KDLS",
    "myrtle_creek_or": "KMFR",
    "paisley_or": "KLKV",
    "pendleton_or": "KPDT",
    "prairie_city_or": "KRDM",  # nearest ASOS
    "redmond_or": "KRDM",
    "roseburg_or": "KRBG",
    "sweet_home_or": "KEUG",
    "vida_or": "KEUG",
    # Oregon — existing
    "blue_river_or": "KEUG",
    "camp_sherman_or": "KRDM",
    "cascade_id": "KDIJ",
    "cle_elum_wa": "KELN",
    "detroit_or": "KSLE",
    "entiat_wa": "KEAT",
    "featherville_pine_id": "KBOI",
    "garden_valley_id": "KBOI",
    "gates_or": "KSLE",
    "hailey_id": "KSUN",
    "hamilton_mt": "KHLN",
    "ketchum_sun_valley_id": "KSUN",
    "lincoln_mt": "KHLN",
    "lolo_mt": "KMSO",
    "lowman_id": "KBOI",
    "manson_wa": "KEAT",
    "oakridge_or": "KEUG",
    "omak_okanogan_wa": "KOMK",
    "pateros_wa": "KOMK",
    "phoenix_or": "KMFR",
    "red_lodge_mt": "KBIL",
    "roslyn_wa": "KELN",
    "salmon_id": "KSMN",
    "seeley_lake_mt": "KMSO",
    "stanley_id": "KSUN",
    "stevensville_mt": "KMSO",
    "sunriver_or": "KRDM",
    "superior_mt": "KMSO",
    "talent_or": "KMFR",
    "twisp_wa": "KOMK",
    "west_yellowstone_mt": "KWYS",
    "winthrop_wa": "KOMK",
}
