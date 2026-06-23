import 'package:flutter/material.dart';
import 'package:supabase_flutter/supabase_flutter.dart';
import 'package:url_launcher/url_launcher.dart';
import 'package:timeago/timeago.dart' as timeago;

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();

  // Initialisation de Supabase avec les clés du projet
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
      title: 'Veille Emploi',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(
          seedColor: const Color(0xFF0D47A1),
          brightness: Brightness.light,
        ),
        useMaterial3: true,
      ),
      darkTheme: ThemeData(
        colorScheme: ColorScheme.fromSeed(
          seedColor: const Color(0xFF1976D2),
          brightness: Brightness.dark,
        ),
        useMaterial3: true,
      ),
      themeMode: ThemeMode.system, // S'adapte au mode du téléphone
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
  bool _isLoading = true;

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
          .limit(100);
      
      setState(() {
        _opportunites = List<Map<String, dynamic>>.from(data);
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

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Opportunités Bénin', style: TextStyle(fontWeight: FontWeight.bold)),
        centerTitle: true,
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _fetchOpportunites,
          ),
        ],
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : _opportunites.isEmpty
              ? const Center(
                  child: Text('Aucune offre trouvée.', style: TextStyle(fontSize: 18)),
                )
              : RefreshIndicator(
                  onRefresh: _fetchOpportunites,
                  child: ListView.builder(
                    padding: const EdgeInsets.all(12),
                    itemCount: _opportunites.length,
                    itemBuilder: (context, index) {
                      final opp = _opportunites[index];
                      final dateStr = opp['date_decouverte'] as String?;
                      DateTime? dateObj;
                      if (dateStr != null) {
                        dateObj = DateTime.tryParse(dateStr);
                      }

                      return Card(
                        elevation: 2,
                        margin: const EdgeInsets.only(bottom: 16),
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
                        child: InkWell(
                          borderRadius: BorderRadius.circular(16),
                          onTap: () => _openLink(opp['lien']),
                          child: Padding(
                            padding: const EdgeInsets.all(16.0),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Row(
                                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                                  children: [
                                    Container(
                                      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                                      decoration: BoxDecoration(
                                        color: Colors.blueAccent.withOpacity(0.1),
                                        borderRadius: BorderRadius.circular(12),
                                      ),
                                      child: Text(
                                        opp['type'] ?? 'Offre',
                                        style: const TextStyle(
                                          color: Colors.blueAccent,
                                          fontWeight: FontWeight.bold,
                                          fontSize: 12,
                                        ),
                                      ),
                                    ),
                                    if (dateObj != null)
                                      Text(
                                        timeago.format(dateObj, locale: 'fr'),
                                        style: const TextStyle(color: Colors.grey, fontSize: 12),
                                      ),
                                  ],
                                ),
                                const SizedBox(height: 12),
                                Text(
                                  opp['titre'] ?? 'Sans Titre',
                                  style: const TextStyle(
                                    fontSize: 18,
                                    fontWeight: FontWeight.bold,
                                  ),
                                ),
                                const SizedBox(height: 8),
                                if (opp['source'] != null) ...[
                                  Row(
                                    children: [
                                      const Icon(Icons.language, size: 16, color: Colors.grey),
                                      const SizedBox(width: 4),
                                      Text(
                                        opp['source'],
                                        style: const TextStyle(color: Colors.grey, fontSize: 14),
                                      ),
                                    ],
                                  ),
                                  const SizedBox(height: 8),
                                ],
                                Text(
                                  opp['resume'] != null && opp['resume'].length > 150
                                      ? '${opp['resume'].substring(0, 150)}...'
                                      : (opp['resume'] ?? ''),
                                  style: const TextStyle(fontSize: 14),
                                ),
                                const SizedBox(height: 12),
                                const Divider(),
                                Row(
                                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                                  children: [
                                    Text(
                                      opp['date_limite'] != null && opp['date_limite'].isNotEmpty
                                          ? 'Limite: ${opp['date_limite']}'
                                          : '',
                                      style: const TextStyle(
                                        color: Colors.redAccent,
                                        fontWeight: FontWeight.w500,
                                        fontSize: 13,
                                      ),
                                    ),
                                    const Text(
                                      'Voir l\'offre →',
                                      style: TextStyle(
                                        color: Colors.blue,
                                        fontWeight: FontWeight.bold,
                                      ),
                                    ),
                                  ],
                                ),
                              ],
                            ),
                          ),
                        ),
                      );
                    },
                  ),
                ),
    );
  }
}
