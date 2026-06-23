import 'package:flutter/material.dart';
import 'package:supabase_flutter/supabase_flutter.dart';
import 'package:url_launcher/url_launcher.dart';
import 'package:timeago/timeago.dart' as timeago;

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();

  await Supabase.initialize(
    url: 'https://eounqfjlfkkqyjnvpqcx.supabase.co',
    anonKey: 'sb_publishable_Wx8W4DOPY0N3HcpjAnmIhA_vMqutAex',
  );

  timeago.setLocaleMessages('fr', timeago.FrMessages());

  runApp(const MyApp());
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
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
      themeMode: ThemeMode.system,
      home: const HomePage(),
    );
  }
}

class HomePage extends StatefulWidget {
  const HomePage({super.key});

  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> {
  final SupabaseClient supabase = Supabase.instance.client;
  List<Map<String, dynamic>> _opportunites = [];
  List<Map<String, dynamic>> _filteredOpportunites = [];
  bool _isLoading = true;
  String _selectedCategory = 'Tous';
  String _searchQuery = '';

  final List<String> _categories = ['Tous', 'Emploi', 'Stage', 'Bourse', 'Concours'];

  @override
  void initState() {
    super.initState();
    _fetchOpportunites();
  }

  Future<void> _fetchOpportunites() async {
    setState(() => _isLoading = true);
    try {
      final data = await supabase
          .from('opportunites')
          .select()
          .order('date_decouverte', ascending: false)
          .limit(200);
      
      setState(() {
        _opportunites = List<Map<String, dynamic>>.from(data);
        _applyFilters();
      });
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Erreur: $e')),
        );
      }
    } finally {
      if (mounted) {
        setState(() => _isLoading = false);
      }
    }
  }

  void _applyFilters() {
    setState(() {
      _filteredOpportunites = _opportunites.where((opp) {
        final matchesCategory = _selectedCategory == 'Tous' || 
            (opp['type'] != null && opp['type'].toString().toLowerCase().contains(_selectedCategory.toLowerCase()));
        
        final matchesSearch = _searchQuery.isEmpty ||
            (opp['titre'] != null && opp['titre'].toString().toLowerCase().contains(_searchQuery.toLowerCase())) ||
            (opp['resume'] != null && opp['resume'].toString().toLowerCase().contains(_searchQuery.toLowerCase()));
            
        return matchesCategory && matchesSearch;
      }).toList();
    });
  }

  Future<void> _openLink(String url) async {
    final Uri uri = Uri.parse(url);
    if (!await launchUrl(uri, mode: LaunchMode.externalApplication)) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Impossible d\'ouvrir le lien')),
        );
      }
    }
  }

  Color _getCategoryColor(String type) {
    type = type.toLowerCase();
    if (type.contains('emploi')) return Colors.blue;
    if (type.contains('stage')) return Colors.orange;
    if (type.contains('bourse')) return Colors.purple;
    if (type.contains('concours')) return Colors.red;
    return Colors.grey;
  }

  IconData _getCategoryIcon(String type) {
    type = type.toLowerCase();
    if (type.contains('emploi')) return Icons.work;
    if (type.contains('stage')) return Icons.school;
    if (type.contains('bourse')) return Icons.account_balance;
    if (type.contains('concours')) return Icons.assignment;
    return Icons.business_center;
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    
    return Scaffold(
      body: CustomScrollView(
        slivers: [
          SliverAppBar(
            expandedHeight: 180.0,
            floating: true,
            pinned: true,
            elevation: 0,
            flexibleSpace: FlexibleSpaceBar(
              background: Container(
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    colors: isDark 
                      ? [const Color(0xFF1E3A8A), const Color(0xFF0F172A)]
                      : [const Color(0xFF2563EB), const Color(0xFF60A5FA)],
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                  ),
                ),
                child: Center(
                  child: Padding(
                    padding: const EdgeInsets.only(top: 40.0),
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        const Icon(Icons.rocket_launch, size: 40, color: Colors.white),
                        const SizedBox(height: 8),
                        const Text(
                          'Lynha opportunité',
                          style: TextStyle(
                            color: Colors.white,
                            fontSize: 26,
                            fontWeight: FontWeight.bold,
                            letterSpacing: 1.2,
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            ),
            bottom: PreferredSize(
              preferredSize: const Size.fromHeight(60),
              child: Container(
                height: 60,
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                decoration: BoxDecoration(
                  color: Theme.of(context).scaffoldBackgroundColor,
                  borderRadius: const BorderRadius.only(
                    topLeft: Radius.circular(30),
                    topRight: Radius.circular(30),
                  ),
                ),
                child: TextField(
                  onChanged: (value) {
                    _searchQuery = value;
                    _applyFilters();
                  },
                  decoration: InputDecoration(
                    hintText: 'Rechercher (ex: Informatique, Cotonou...)',
                    prefixIcon: const Icon(Icons.search, color: Colors.blue),
                    filled: true,
                    fillColor: isDark ? Colors.grey[800] : Colors.grey[200],
                    contentPadding: const EdgeInsets.symmetric(vertical: 0),
                    border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(30),
                      borderSide: BorderSide.none,
                    ),
                  ),
                ),
              ),
            ),
          ),
          
          // Categories Filter
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
                      selected: isSelected,
                      label: Text(
                        category,
                        style: TextStyle(
                          color: isSelected ? Colors.white : (isDark ? Colors.white70 : Colors.black87),
                          fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
                        ),
                      ),
                      backgroundColor: isDark ? Colors.grey[800] : Colors.grey[200],
                      selectedColor: const Color(0xFF2563EB),
                      checkmarkColor: Colors.white,
                      onSelected: (bool selected) {
                        setState(() {
                          _selectedCategory = category;
                          _applyFilters();
                        });
                      },
                    ),
                  );
                },
              ),
            ),
          ),

          // Main List
          if (_isLoading)
            const SliverFillRemaining(
              child: Center(child: CircularProgressIndicator()),
            )
          else if (_filteredOpportunites.isEmpty)
            SliverFillRemaining(
              child: Center(
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Icon(Icons.inbox_outlined, size: 80, color: Colors.grey[400]),
                    const SizedBox(height: 16),
                    Text(
                      'Aucune offre trouvée.',
                      style: TextStyle(fontSize: 18, color: Colors.grey[600]),
                    ),
                  ],
                ),
              ),
            )
          else
            SliverPadding(
              padding: const EdgeInsets.only(left: 16, right: 16, bottom: 24),
              sliver: SliverList(
                delegate: SliverChildBuilderDelegate(
                  (context, index) {
                    final opp = _filteredOpportunites[index];
                    final dateStr = opp['date_decouverte'] as String?;
                    DateTime? dateObj;
                    if (dateStr != null) {
                      dateObj = DateTime.tryParse(dateStr);
                    }
                    
                    final type = opp['type'] ?? 'Offre';
                    final color = _getCategoryColor(type);
                    final icon = _getCategoryIcon(type);

                    return Container(
                      margin: const EdgeInsets.only(bottom: 16),
                      decoration: BoxDecoration(
                        color: Theme.of(context).cardColor,
                        borderRadius: BorderRadius.circular(20),
                        boxShadow: [
                          BoxShadow(
                            color: Colors.black.withOpacity(isDark ? 0.3 : 0.05),
                            blurRadius: 10,
                            offset: const Offset(0, 4),
                          ),
                        ],
                      ),
                      child: Material(
                        color: Colors.transparent,
                        child: InkWell(
                          borderRadius: BorderRadius.circular(20),
                          onTap: () => _openLink(opp['lien']),
                          child: Padding(
                            padding: const EdgeInsets.all(20.0),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                // HEADER : Type et Date
                                Row(
                                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                                  children: [
                                    Container(
                                      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                                      decoration: BoxDecoration(
                                        color: color.withOpacity(0.15),
                                        borderRadius: BorderRadius.circular(20),
                                      ),
                                      child: Row(
                                        mainAxisSize: MainAxisSize.min,
                                        children: [
                                          Icon(icon, size: 14, color: color),
                                          const SizedBox(width: 6),
                                          Text(
                                            type.toUpperCase(),
                                            style: TextStyle(
                                              color: color,
                                              fontWeight: FontWeight.w800,
                                              fontSize: 11,
                                              letterSpacing: 0.5,
                                            ),
                                          ),
                                        ],
                                      ),
                                    ),
                                    if (dateObj != null)
                                      Row(
                                        children: [
                                          Icon(Icons.access_time, size: 14, color: Colors.grey[500]),
                                          const SizedBox(width: 4),
                                          Text(
                                            timeago.format(dateObj, locale: 'fr'),
                                            style: TextStyle(color: Colors.grey[500], fontSize: 12),
                                          ),
                                        ],
                                      ),
                                  ],
                                ),
                                const SizedBox(height: 16),
                                
                                // TITRE
                                Text(
                                  opp['titre'] ?? 'Nouvelle opportunité',
                                  style: const TextStyle(
                                    fontSize: 18,
                                    fontWeight: FontWeight.bold,
                                    height: 1.3,
                                  ),
                                ),
                                
                                const SizedBox(height: 8),
                                
                                // SOURCE
                                if (opp['source'] != null)
                                  Row(
                                    children: [
                                      Icon(Icons.language, size: 14, color: Colors.blueGrey[400]),
                                      const SizedBox(width: 6),
                                      Text(
                                        opp['source'],
                                        style: TextStyle(
                                          color: Colors.blueGrey[400], 
                                          fontSize: 13,
                                          fontWeight: FontWeight.w500,
                                        ),
                                      ),
                                    ],
                                  ),
                                  
                                const SizedBox(height: 12),
                                
                                // RESUME
                                Container(
                                  padding: const EdgeInsets.all(12),
                                  decoration: BoxDecoration(
                                    color: isDark ? Colors.grey[850] : Colors.grey[50],
                                    borderRadius: BorderRadius.circular(12),
                                    border: Border.all(
                                      color: isDark ? Colors.grey[800]! : Colors.grey[200]!,
                                    ),
                                  ),
                                  child: Text(
                                    opp['resume'] != null && opp['resume'].length > 150
                                        ? '${opp['resume'].substring(0, 150)}...'
                                        : (opp['resume'] ?? ''),
                                    style: TextStyle(
                                      fontSize: 14,
                                      height: 1.5,
                                      color: isDark ? Colors.grey[300] : Colors.grey[700],
                                    ),
                                  ),
                                ),
                                
                                const SizedBox(height: 16),
                                
                                // FOOTER : Limite et Bouton
                                Row(
                                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                                  children: [
                                    if (opp['date_limite'] != null && opp['date_limite'] != 'Voir sur le site')
                                      Row(
                                        children: [
                                          const Icon(Icons.event_busy, size: 14, color: Colors.redAccent),
                                          const SizedBox(width: 4),
                                          Text(
                                            'Limite: ${opp['date_limite']}',
                                            style: const TextStyle(
                                              color: Colors.redAccent,
                                              fontWeight: FontWeight.bold,
                                              fontSize: 12,
                                            ),
                                          ),
                                        ],
                                      )
                                    else
                                      const SizedBox.shrink(),
                                      
                                    Container(
                                      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                                      decoration: BoxDecoration(
                                        color: const Color(0xFF2563EB),
                                        borderRadius: BorderRadius.circular(20),
                                      ),
                                      child: const Row(
                                        mainAxisSize: MainAxisSize.min,
                                        children: [
                                          Text(
                                            'Voir l\'offre',
                                            style: TextStyle(
                                              color: Colors.white,
                                              fontWeight: FontWeight.bold,
                                              fontSize: 13,
                                            ),
                                          ),
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
                  },
                  childCount: _filteredOpportunites.length,
                ),
              ),
            ),
        ],
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: _fetchOpportunites,
        backgroundColor: const Color(0xFF2563EB),
        child: const Icon(Icons.refresh, color: Colors.white),
      ),
    );
  }
}
