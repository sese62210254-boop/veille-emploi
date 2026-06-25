import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:supabase_flutter/supabase_flutter.dart';
import 'package:url_launcher/url_launcher.dart';
import 'package:timeago/timeago.dart' as timeago;
import 'package:carousel_slider/carousel_slider.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:share_plus/share_plus.dart';
import 'theme_notifier.dart';

Future<void> main() async {
  try {
    WidgetsFlutterBinding.ensureInitialized();
    await Firebase.initializeApp();

    FirebaseMessaging messaging = FirebaseMessaging.instance;
    await messaging.requestPermission(alert: true, badge: true, sound: true);
    // Subscription initiale globale (par defaut tout le monde l'a)
    await messaging.subscribeToTopic('nouvelles_offres');

    await Supabase.initialize(
      url: 'https://eounqfjlfkkqyjnvpqcx.supabase.co',
      anonKey: 'sb_publishable_Wx8W4DOPY0N3HcpjAnmIhA_vMqutAex',
    );

    timeago.setLocaleMessages('fr', timeago.FrMessages());
    runApp(const MyApp());
  } catch (e, stackTrace) {
    runApp(MaterialApp(
      home: Scaffold(
        body: SafeArea(
          child: SingleChildScrollView(
            child: Text('ERREUR FATALE:\n\n\n', style: const TextStyle(color: Colors.red, fontSize: 12)),
          ),
        ),
      ),
    ));
  }
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return ValueListenableBuilder<ThemeMode>(
      valueListenable: themeNotifier,
      builder: (_, ThemeMode currentMode, __) {
        return MaterialApp(
          title: 'Lynha opportunité',
          debugShowCheckedModeBanner: false,
          theme: ThemeData(
            colorScheme: ColorScheme.fromSeed(
              seedColor: const Color(0xFF2563EB),
              brightness: Brightness.light,
              surface: const Color(0xFFF8FAFC),
            ),
            useMaterial3: true,
            fontFamily: 'Roboto',
          ),
          darkTheme: ThemeData(
            colorScheme: ColorScheme.fromSeed(
              seedColor: const Color(0xFF3B82F6),
              brightness: Brightness.dark,
              surface: const Color(0xFF0F172A),
            ),
            useMaterial3: true,
            fontFamily: 'Roboto',
          ),
          themeMode: currentMode,
          home: const MainScreen(),
        );
      },
    );
  }
}

class MainScreen extends StatefulWidget {
  const MainScreen({super.key});

  @override
  State<MainScreen> createState() => _MainScreenState();
}

class _MainScreenState extends State<MainScreen> {
  int _currentIndex = 0;

  final List<Widget> _pages = [
    const HomeTab(),
    const FavoritesTab(),
    const SettingsTab(),
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: IndexedStack(
        index: _currentIndex,
        children: _pages,
      ),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _currentIndex,
        onDestinationSelected: (index) {
          setState(() {
            _currentIndex = index;
          });
        },
        destinations: const [
          NavigationDestination(
            icon: Icon(Icons.home_outlined),
            selectedIcon: Icon(Icons.home),
            label: 'Accueil',
          ),
          NavigationDestination(
            icon: Icon(Icons.favorite_outline),
            selectedIcon: Icon(Icons.favorite),
            label: 'Favoris',
          ),
          NavigationDestination(
            icon: Icon(Icons.settings_outlined),
            selectedIcon: Icon(Icons.settings),
            label: 'Réglages',
          ),
        ],
      ),
    );
  }
}

// ----------------------------------------------------------------------
// GESTIONNAIRE DES FAVORIS (Shared Preferences)
// ----------------------------------------------------------------------
class FavoritesManager {
  static const String _key = 'favoris_list';

  static Future<List<Map<String, dynamic>>> getFavorites() async {
    final prefs = await SharedPreferences.getInstance();
    final String? jsonStr = prefs.getString(_key);
    if (jsonStr == null) return [];
    final List<dynamic> decoded = jsonDecode(jsonStr);
    return decoded.cast<Map<String, dynamic>>();
  }

  static Future<void> toggleFavorite(Map<String, dynamic> opp) async {
    final prefs = await SharedPreferences.getInstance();
    List<Map<String, dynamic>> favorites = await getFavorites();
    
    final int index = favorites.indexWhere((f) => f['lien'] == opp['lien']);
    if (index >= 0) {
      favorites.removeAt(index);
    } else {
      favorites.add(opp);
    }
    
    await prefs.setString(_key, jsonEncode(favorites));
  }

  static Future<bool> isFavorite(String lien) async {
    final favorites = await getFavorites();
    return favorites.any((f) => f['lien'] == lien);
  }
}

// ----------------------------------------------------------------------
// WIDGET D'OFFRE (Carte reutilisable pour Accueil et Favoris)
// ----------------------------------------------------------------------
class OpportunityCard extends StatefulWidget {
  final Map<String, dynamic> opp;
  const OpportunityCard({super.key, required this.opp});

  @override
  State<OpportunityCard> createState() => _OpportunityCardState();
}

class _OpportunityCardState extends State<OpportunityCard> {
  bool _isFav = false;

  @override
  void initState() {
    super.initState();
    _checkFav();
  }

  Future<void> _checkFav() async {
    final isFav = await FavoritesManager.isFavorite(widget.opp['lien']);
    if (mounted) setState(() => _isFav = isFav);
  }

  Future<void> _toggleFav() async {
    await FavoritesManager.toggleFavorite(widget.opp);
    await _checkFav();
  }
  
  Future<void> _share() async {
    final url = widget.opp['lien'];
    final titre = widget.opp['titre'];
    await Share.share('🚀 Lynha opportunité : $titre\n\nLien : $url');
  }

  Future<void> _openLink() async {
    final url = widget.opp['lien'];
    if (url != null) {
      final Uri uri = Uri.parse(url);
      if (!await launchUrl(uri, mode: LaunchMode.externalApplication)) {
        if (mounted) ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Impossible d\'ouvrir le lien')));
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final opp = widget.opp;
    
    DateTime? dateObj;
    if (opp['date_decouverte'] != null) {
      dateObj = DateTime.tryParse(opp['date_decouverte'].toString());
    }
    
    Color typeColor = Colors.blue;
    String type = opp['type']?.toString().toUpperCase() ?? 'OFFRE';
    if (type.contains('STAGE')) typeColor = Colors.orange;
    if (type.contains('BOURSE')) typeColor = Colors.green;
    if (type.contains('CONCOURS')) typeColor = Colors.purple;

    return Container(
      margin: const EdgeInsets.only(bottom: 16),
      decoration: BoxDecoration(
        color: isDark ? const Color(0xFF1E293B) : Colors.white,
        borderRadius: BorderRadius.circular(16),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(isDark ? 0.3 : 0.05),
            blurRadius: 10,
            offset: const Offset(0, 4),
          ),
        ],
        border: Border.all(
          color: isDark ? Colors.grey[800]! : Colors.grey[200]!,
          width: 1,
        ),
      ),
      child: Material(
        color: Colors.transparent,
        borderRadius: BorderRadius.circular(16),
        child: InkWell(
          onTap: _openLink,
          borderRadius: BorderRadius.circular(16),
          child: Padding(
            padding: const EdgeInsets.all(16.0),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Header (Type + Date + Boutons d'action)
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                      decoration: BoxDecoration(
                        color: typeColor.withOpacity(0.15),
                        borderRadius: BorderRadius.circular(20),
                      ),
                      child: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Icon(Icons.work, size: 14, color: typeColor),
                          const SizedBox(width: 6),
                          Text(
                            type,
                            style: TextStyle(color: typeColor, fontWeight: FontWeight.w800, fontSize: 11),
                          ),
                        ],
                      ),
                    ),
                    Row(
                      children: [
                        if (dateObj != null)
                          Text(
                            timeago.format(dateObj, locale: 'fr'),
                            style: TextStyle(color: Colors.grey[500], fontSize: 12),
                          ),
                        const SizedBox(width: 8),
                        IconButton(
                          icon: const Icon(Icons.share_outlined, size: 20),
                          onPressed: _share,
                          padding: EdgeInsets.zero,
                          constraints: const BoxConstraints(),
                        ),
                        const SizedBox(width: 12),
                        IconButton(
                          icon: Icon(_isFav ? Icons.favorite : Icons.favorite_outline, size: 20, color: _isFav ? Colors.red : null),
                          onPressed: _toggleFav,
                          padding: EdgeInsets.zero,
                          constraints: const BoxConstraints(),
                        ),
                      ],
                    ),
                  ],
                ),
                const SizedBox(height: 16),
                
                Text(
                  opp['titre'] ?? 'Nouvelle opportunité',
                  style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold, height: 1.3),
                ),
                const SizedBox(height: 8),
                if (opp['source'] != null)
                  Row(
                    children: [
                      Icon(Icons.language, size: 14, color: Colors.blueGrey[400]),
                      const SizedBox(width: 6),
                      Text(
                        opp['source'],
                        style: TextStyle(color: Colors.blueGrey[400], fontSize: 13, fontWeight: FontWeight.w500),
                      ),
                    ],
                  ),
                const SizedBox(height: 12),
                Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: isDark ? Colors.grey[850] : Colors.grey[50],
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(color: isDark ? Colors.grey[800]! : Colors.grey[200]!),
                  ),
                  child: Text(
                    opp['resume'] != null && opp['resume'].length > 150 ? '${opp['resume'].substring(0, 150)}...' : (opp['resume'] ?? ''),
                    style: TextStyle(fontSize: 14, height: 1.5, color: isDark ? Colors.grey[300] : Colors.grey[700]),
                  ),
                ),
                const SizedBox(height: 16),
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    if (opp['date_limite'] != null && opp['date_limite'] != 'Voir sur le site')
                      Row(
                        children: [
                          const Icon(Icons.event_busy, size: 14, color: Colors.redAccent),
                          const SizedBox(width: 4),
                          Text('Limite: ', style: const TextStyle(color: Colors.redAccent, fontWeight: FontWeight.bold, fontSize: 12)),
                        ],
                      )
                    else
                      const SizedBox.shrink(),
                      
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                      decoration: BoxDecoration(color: const Color(0xFF2563EB), borderRadius: BorderRadius.circular(20)),
                      child: const Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Text('Voir l\'offre', style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 13)),
                          SizedBox(width: 4),
                          Icon(Icons.arrow_forward, size: 14, color: Colors.white),
                        ],
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

// ----------------------------------------------------------------------
// ONGLET 1: ACCUEIL
// ----------------------------------------------------------------------
class HomeTab extends StatefulWidget {
  const HomeTab({super.key});

  @override
  State<HomeTab> createState() => _HomeTabState();
}

class _HomeTabState extends State<HomeTab> {
  final SupabaseClient supabase = Supabase.instance.client;
  List<Map<String, dynamic>> _opportunites = [];
  List<Map<String, dynamic>> _filteredOpportunites = [];
  bool _isLoading = true;
  String _selectedCategory = 'Tous';
  String _searchQuery = '';
  String _selectedDateFilter = 'Toutes';
  final List<String> _categories = ['Tous', 'Emploi', 'Stage', 'Bourse', 'Concours'];
  final List<String> _dateFilters = ['Toutes', "Aujourd'hui", 'Hier', 'Cette semaine'];

  @override
  void initState() {
    super.initState();
    _fetchOpportunites();
  }

  void _fetchOpportunites() {
    supabase.from('opportunites').stream(primaryKey: ['id']).order('date_decouverte', ascending: false).limit(200).listen((data) {
      if (mounted) {
        setState(() {
          _opportunites = List<Map<String, dynamic>>.from(data);
          _applyFilters();
          _isLoading = false;
        });
      }
    }, onError: (error) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Erreur: ')));
        setState(() => _isLoading = false);
      }
    });
  }

  void _applyFilters() {
    setState(() {
      _filteredOpportunites = _opportunites.where((opp) {
        final matchesCategory = _selectedCategory == 'Tous' || (opp['type'] != null && opp['type'].toString().toLowerCase().contains(_selectedCategory.toLowerCase()));
        final matchesSearch = _searchQuery.isEmpty ||
            (opp['titre'] != null && opp['titre'].toString().toLowerCase().contains(_searchQuery.toLowerCase())) ||
            (opp['resume'] != null && opp['resume'].toString().toLowerCase().contains(_searchQuery.toLowerCase()));
            
        bool matchesDate = true;
        if (_selectedDateFilter != 'Toutes' && opp['date_decouverte'] != null) {
          final oppDate = DateTime.tryParse(opp['date_decouverte'].toString());
          if (oppDate != null) {
            final now = DateTime.now();
            final difference = now.difference(oppDate).inDays;
            
            if (_selectedDateFilter == "Aujourd'hui") {
              matchesDate = difference == 0 || (now.day == oppDate.day && now.month == oppDate.month && now.year == oppDate.year);
            } else if (_selectedDateFilter == 'Hier') {
              final yesterday = now.subtract(const Duration(days: 1));
              matchesDate = yesterday.day == oppDate.day && yesterday.month == oppDate.month && yesterday.year == oppDate.year;
            } else if (_selectedDateFilter == 'Cette semaine') {
              matchesDate = difference <= 7;
            }
          }
        }
        return matchesCategory && matchesSearch && matchesDate;
      }).toList();
    });
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    
    return Scrollbar(
      thickness: 8.0,
      radius: const Radius.circular(10),
      interactive: true,
      child: RefreshIndicator(
        onRefresh: _fetchOpportunites,
        child: CustomScrollView(
          physics: const AlwaysScrollableScrollPhysics(),
          slivers: [
            // APP BAR ET CARROUSEL
            SliverAppBar(
              expandedHeight: 220.0,
              floating: false,
              pinned: true,
              elevation: 0,
              backgroundColor: isDark ? const Color(0xFF0F172A) : const Color(0xFF2563EB),
              flexibleSpace: FlexibleSpaceBar(
                background: Stack(
                  fit: StackFit.expand,
                  children: [
                    CarouselSlider(
                      options: CarouselOptions(
                        autoPlay: true,
                        viewportFraction: 1.0,
                        enlargeCenterPage: false,
                        autoPlayCurve: Curves.fastOutSlowIn,
                        enableInfiniteScroll: true,
                        autoPlayAnimationDuration: const Duration(milliseconds: 800),
                      ),
                      items: [
                        'assets/images/hr-recruiters-applicant-reading-employment-agreement-terms.jpg',
                        'assets/images/joyful-successful-sales-agent-presenting-content-tablet.jpg',
                        'assets/images/women-working-together-office.jpg',
                        'assets/images/human-resources-people-networking-concept.jpg',
                      ].map((item) => Image.asset(item, fit: BoxFit.cover)).toList(),
                    ),
                    Container(
                      decoration: BoxDecoration(
                        gradient: LinearGradient(
                          colors: [Colors.black.withOpacity(0.6), Colors.black.withOpacity(0.2)],
                          begin: Alignment.topCenter,
                          end: Alignment.bottomCenter,
                        ),
                      ),
                    ),
                    Center(
                      child: Padding(
                        padding: const EdgeInsets.only(top: 20.0),
                        child: Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: const [
                            Icon(Icons.rocket_launch, size: 40, color: Colors.white),
                            SizedBox(height: 8),
                            Text(
                              'Lynha opportunité',
                              style: TextStyle(color: Colors.white, fontSize: 26, fontWeight: FontWeight.bold, letterSpacing: 1.2),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ],
                ),
              ),
              bottom: PreferredSize(
                preferredSize: const Size.fromHeight(60),
                child: Container(
                  height: 60,
                  padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                  decoration: BoxDecoration(
                    color: Theme.of(context).scaffoldBackgroundColor,
                    borderRadius: const BorderRadius.only(topLeft: Radius.circular(30), topRight: Radius.circular(30)),
                  ),
                  child: TextField(
                    onChanged: (value) { _searchQuery = value; _applyFilters(); },
                    decoration: InputDecoration(
                      hintText: 'Rechercher (ex: Informatique...)',
                      prefixIcon: const Icon(Icons.search, color: Colors.blue),
                      filled: true,
                      fillColor: isDark ? Colors.grey[800] : Colors.grey[200],
                      contentPadding: const EdgeInsets.symmetric(vertical: 0),
                      border: OutlineInputBorder(borderRadius: BorderRadius.circular(30), borderSide: BorderSide.none),
                    ),
                  ),
                ),
              ),
            ),
            // FILTRE CATEGORIES
            SliverToBoxAdapter(
              child: SizedBox(
                height: 60,
                child: ListView.builder(
                  scrollDirection: Axis.horizontal,
                  padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                  itemCount: _categories.length,
                  itemBuilder: (context, index) {
                    final category = _categories[index];
                    final isSelected = _selectedCategory == category;
                    return Padding(
                      padding: const EdgeInsets.only(right: 8.0),
                      child: FilterChip(
                        label: Text(category, style: TextStyle(color: isSelected ? Colors.white : (isDark ? Colors.white70 : Colors.black87), fontWeight: isSelected ? FontWeight.bold : FontWeight.normal)),
                        selected: isSelected,
                        backgroundColor: isDark ? Colors.grey[800] : Colors.grey[200],
                        selectedColor: const Color(0xFF2563EB),
                        checkmarkColor: Colors.white,
                        onSelected: (bool selected) { setState(() { _selectedCategory = category; _applyFilters(); }); },
                      ),
                    );
                  },
                ),
              ),
            ),
            // FILTRE DATES
            SliverToBoxAdapter(
              child: SizedBox(
                height: 50,
                child: ListView.builder(
                  scrollDirection: Axis.horizontal,
                  padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 0),
                  itemCount: _dateFilters.length,
                  itemBuilder: (context, index) {
                    final filter = _dateFilters[index];
                    final isSelected = _selectedDateFilter == filter;
                    return Padding(
                      padding: const EdgeInsets.only(right: 8.0),
                      child: ActionChip(
                        label: Text(filter, style: TextStyle(color: isSelected ? Colors.white : (isDark ? Colors.white70 : Colors.black87), fontSize: 12)),
                        backgroundColor: isSelected ? Colors.green[600] : (isDark ? Colors.grey[800] : Colors.grey[300]),
                        onPressed: () { setState(() { _selectedDateFilter = filter; _applyFilters(); }); },
                      ),
                    );
                  },
                ),
              ),
            ),
            // LISTE DES OFFRES
            if (_isLoading)
              const SliverFillRemaining(child: Center(child: CircularProgressIndicator()))
            else if (_filteredOpportunites.isEmpty)
              SliverFillRemaining(
                child: Center(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Icon(Icons.search_off, size: 64, color: Colors.grey[400]),
                      const SizedBox(height: 16),
                      Text('Aucune offre trouvée.', style: TextStyle(fontSize: 18, color: Colors.grey[600], fontWeight: FontWeight.bold)),
                    ],
                  ),
                ),
              )
            else
              SliverPadding(
                padding: const EdgeInsets.all(16.0),
                sliver: SliverList(
                  delegate: SliverChildBuilderDelegate(
                    (context, index) {
                      return OpportunityCard(opp: _filteredOpportunites[index]);
                    },
                    childCount: _filteredOpportunites.length,
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }
}

// ----------------------------------------------------------------------
// ONGLET 2: FAVORIS
// ----------------------------------------------------------------------
class FavoritesTab extends StatefulWidget {
  const FavoritesTab({super.key});

  @override
  State<FavoritesTab> createState() => _FavoritesTabState();
}

class _FavoritesTabState extends State<FavoritesTab> {
  List<Map<String, dynamic>> _favorites = [];

  @override
  void initState() {
    super.initState();
    _loadFavorites();
  }

  Future<void> _loadFavorites() async {
    final favs = await FavoritesManager.getFavorites();
    setState(() {
      _favorites = favs;
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Mes Favoris ❤️', style: TextStyle(fontWeight: FontWeight.bold)),
      ),
      body: _favorites.isEmpty
          ? const Center(
              child: Text(
                'Aucun favori pour le moment.',
                style: TextStyle(fontSize: 18, color: Colors.grey),
              ),
            )
          : ListView.builder(
              padding: const EdgeInsets.all(16.0),
              itemCount: _favorites.length,
              itemBuilder: (context, index) {
                return OpportunityCard(opp: _favorites[index]);
              },
            ),
    );
  }
}

// ----------------------------------------------------------------------
// ONGLET 3: REGLAGES (Mode sombre & Alertes)
// ----------------------------------------------------------------------
class SettingsTab extends StatefulWidget {
  const SettingsTab({super.key});

  @override
  State<SettingsTab> createState() => _SettingsTabState();
}

class _SettingsTabState extends State<SettingsTab> {
  bool _alertsEnabled = true;
  bool _alertEmplois = true;
  bool _alertStages = true;
  bool _alertBourses = true;
  bool _alertConcours = true;

  @override
  void initState() {
    super.initState();
    _loadSettings();
  }

  Future<void> _loadSettings() async {
    final prefs = await SharedPreferences.getInstance();
    setState(() {
      _alertsEnabled = prefs.getBool('alerts_enabled') ?? true;
      _alertEmplois = prefs.getBool('alert_emplois') ?? true;
      _alertStages = prefs.getBool('alert_stages') ?? true;
      _alertBourses = prefs.getBool('alert_bourses') ?? true;
      _alertConcours = prefs.getBool('alert_concours') ?? true;
    });
  }

  Future<void> _saveSetting(String key, bool value) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool(key, value);
    // TODO: Connect Firebase Topics based on these preferences!
    // (Simulate Firebase subscription for now)
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Réglages ⚙️', style: TextStyle(fontWeight: FontWeight.bold)),
      ),
      body: ListView(
        children: [
          const Padding(
            padding: EdgeInsets.all(16.0),
            child: Text('Apparence', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: Colors.blue)),
          ),
          ListTile(
            leading: const Icon(Icons.brightness_auto),
            title: const Text('Système (Défaut)'),
            trailing: themeNotifier.value == ThemeMode.system ? const Icon(Icons.check, color: Colors.blue) : null,
            onTap: () => themeNotifier.toggleTheme(ThemeMode.system),
          ),
          ListTile(
            leading: const Icon(Icons.light_mode),
            title: const Text('Mode Clair'),
            trailing: themeNotifier.value == ThemeMode.light ? const Icon(Icons.check, color: Colors.blue) : null,
            onTap: () => themeNotifier.toggleTheme(ThemeMode.light),
          ),
          ListTile(
            leading: const Icon(Icons.dark_mode),
            title: const Text('Mode Sombre'),
            trailing: themeNotifier.value == ThemeMode.dark ? const Icon(Icons.check, color: Colors.blue) : null,
            onTap: () => themeNotifier.toggleTheme(ThemeMode.dark),
          ),
          
          const Divider(height: 32),
          
          const Padding(
            padding: EdgeInsets.all(16.0),
            child: Text('Mes Alertes (Notifications)', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: Colors.blue)),
          ),
          SwitchListTile(
            title: const Text('Activer les alertes'),
            subtitle: const Text('Recevoir des notifications pour les nouvelles offres'),
            value: _alertsEnabled,
            onChanged: (bool value) {
              setState(() => _alertsEnabled = value);
              _saveSetting('alerts_enabled', value);
            },
          ),
          if (_alertsEnabled) ...[
            SwitchListTile(
              title: const Text('Emplois'),
              value: _alertEmplois,
              onChanged: (bool value) {
                setState(() => _alertEmplois = value);
                _saveSetting('alert_emplois', value);
              },
            ),
            SwitchListTile(
              title: const Text('Stages'),
              value: _alertStages,
              onChanged: (bool value) {
                setState(() => _alertStages = value);
                _saveSetting('alert_stages', value);
              },
            ),
            SwitchListTile(
              title: const Text('Bourses d\'études'),
              value: _alertBourses,
              onChanged: (bool value) {
                setState(() => _alertBourses = value);
                _saveSetting('alert_bourses', value);
              },
            ),
            SwitchListTile(
              title: const Text('Concours'),
              value: _alertConcours,
              onChanged: (bool value) {
                setState(() => _alertConcours = value);
                _saveSetting('alert_concours', value);
              },
            ),
          ],
        ],
      ),
    );
  }
}
