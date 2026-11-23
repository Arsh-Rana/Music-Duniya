package com.musicduniya.app;

import android.content.Context;
import android.os.Handler;
import android.os.Looper;
import android.webkit.JavascriptInterface;
import android.widget.Toast;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.File;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;
import java.net.URLEncoder;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public class ScraperBridge {
    private final Context context;
    private final Handler mainHandler;
    private final ExecutorService executor = Executors.newFixedThreadPool(4);

    public ScraperBridge(Context context) {
        this.context = context;
        this.mainHandler = new Handler(Looper.getMainLooper());
    }

    @JavascriptInterface
    public boolean isNativeApp() {
        return true;
    }

    @JavascriptInterface
    public void showToast(final String message) {
        mainHandler.post(() -> Toast.makeText(context, message, Toast.LENGTH_SHORT).show());
    }

    @JavascriptInterface
    public String getAssetFileContentSync(String fileName) {
        try {
            InputStream is = context.getAssets().open(fileName);
            BufferedReader reader = new BufferedReader(new InputStreamReader(is, "UTF-8"));
            StringBuilder sb = new StringBuilder();
            String line;
            while ((line = reader.readLine()) != null) {
                sb.append(line);
            }
            reader.close();
            return sb.toString();
        } catch (Exception e) {
            return "";
        }
    }

    @JavascriptInterface
    public String getPopularSingersSync() {
        try {
            JSONArray arr = new JSONArray();
            String[][] singers = {
                {"Diljit Dosanjh", "diljit-dosanjh", "https://cover.djpunjab.is/60220/300x250/im_an_artist_bro_diljit_dosanjh.webp", "18.5M monthly listeners", "Verified Artist"},
                {"Karan Aujla", "karan-aujla", "https://cover.djpunjab.is/60446/300x250/aujla_szn_1_karan_aujla.webp", "15.2M monthly listeners", "Verified Artist"},
                {"Sidhu Moose Wala", "sidhu-moose-wala", "https://cover.mr-jatt.im/thumb/521474/GANGSTA-S-DELIGHT.webp", "22.8M monthly listeners", "Legendary Artist"},
                {"Kulbir Jhinjer", "kulbir-jhinjer", "https://lq.djjohal.com/covers_webp/48718/1.webp", "4.2M monthly listeners", "Verified Artist"},
                {"Babbar Brar", "babbar-brar", "https://lq.djjohal.com/covers_webp/48718/1.webp", "2.1M monthly listeners", "Verified Artist"},
                {"Sabar Koti", "sabar-koti", "https://cover.djpunjab.is/42133/300x250/asi_ese_joge_reh_gaye_sabar_koti.webp", "1.8M monthly listeners", "Sufi & Folk"},
                {"Jordan Sandhu", "jordan-sandhu", "https://cover.djpunjab.is/60220/300x250/im_an_artist_bro_diljit_dosanjh.webp", "5.6M monthly listeners", "Verified Artist"},
                {"Amrit Maan", "amrit-maan", "https://cover.djpunjab.is/60446/300x250/aujla_szn_1_karan_aujla.webp", "6.1M monthly listeners", "Verified Artist"},
                {"Sharry Mann", "sharry-mann", "https://cover.djpunjab.is/42133/300x250/asi_ese_joge_reh_gaye_sabar_koti.webp", "4.9M monthly listeners", "Verified Artist"},
                {"Gurdas Maan", "gurdas-maan", "https://lq.djjohal.com/covers_webp/48718/1.webp", "7.3M monthly listeners", "Living Legend"}
            };

            for (String[] s : singers) {
                JSONObject obj = new JSONObject();
                obj.put("name", s[0]);
                obj.put("slug", s[1]);
                obj.put("avatar_url", s[2]);
                obj.put("followers", s[3]);
                obj.put("tag", s[4]);
                arr.put(obj);
            }
            return arr.toString();
        } catch (Exception e) {
            e.printStackTrace();
            return "[]";
        }
    }

    @JavascriptInterface
    public String getSingersByLetterSync(String letter) {
        JSONArray list = new JSONArray();
        try {
            String l = (letter != null && !letter.isEmpty()) ? letter.toLowerCase() : "a";
            String url = "https://djpunjab.is/page/atozartist.php?cat_id=2&main=" + l;
            String html = httpGet(url, "https://djpunjab.is/");

            Pattern p = Pattern.compile("<a[^>]*href=[\"'](/artist/[^\"']+)[\"'][^>]*>(.*?)</a>");
            Matcher m = p.matcher(html);

            while (m.find()) {
                String path = m.group(1);
                String name = m.group(2).replaceAll("<[^>]+>", "").trim();
                if (name.isEmpty() || name.equals("Home") || name.equals("Single Tracks") ||
                    name.equals("A to Z Artists") || name.contains("Next") || name.contains("Previous")) {
                    continue;
                }
                String slug = path.replace("/artist/", "").trim();
                JSONObject obj = new JSONObject();
                obj.put("name", name);
                obj.put("slug", slug);
                obj.put("page_url", "https://djpunjab.is" + path);
                obj.put("letter", l.toUpperCase());
                obj.put("avatar_url", "https://cover.djpunjab.is/default/avatar_" + l + ".webp");
                obj.put("source", "djpunjab");
                list.put(obj);
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
        return list.toString();
    }

    @JavascriptInterface
    public String getSingerSongsSync(String slug) {
        JSONObject result = new JSONObject();
        try {
            String cleanSlug = slug != null ? slug.trim() : "";
            String url = "https://djpunjab.is/artist/" + cleanSlug;
            String html = httpGet(url, "https://djpunjab.is/");

            String name = cleanSlug.replace("-", " ");
            StringBuilder capName = new StringBuilder();
            for (String word : name.split(" ")) {
                if (word.length() > 0) {
                    capName.append(Character.toUpperCase(word.charAt(0))).append(word.substring(1)).append(" ");
                }
            }
            name = capName.toString().trim();

            String avatarUrl = "https://cover.djpunjab.is/60220/300x250/im_an_artist_bro_diljit_dosanjh.webp";
            Pattern pImg = Pattern.compile("<img[^>]*src=[\"'](https://cover\\.djpunjab\\.is/[^\"']+)[\"']");
            Matcher mImg = pImg.matcher(html);
            if (mImg.find()) {
                avatarUrl = mImg.group(1);
            }

            JSONArray songs = new JSONArray();

            // Single tracks: /single-track/...-album-12345.html
            Pattern pSingle = Pattern.compile("<a[^>]*href=[\"'](/single-track/[^\"']+-album-(\\d+)\\.html)[\"'][^>]*>(.*?)</a>");
            Matcher mSingle = pSingle.matcher(html);
            while (mSingle.find()) {
                String path = mSingle.group(1);
                String albId = mSingle.group(2);
                String title = mSingle.group(3).replaceAll("<[^>]+>", "").trim();
                if (!title.isEmpty()) {
                    JSONObject s = new JSONObject();
                    s.put("id", "djpunjab_" + albId);
                    s.put("title", title);
                    s.put("artist", name);
                    s.put("album", name + " Single");
                    s.put("cover_url", avatarUrl);
                    s.put("page_url", "https://djpunjab.is" + path);
                    s.put("source", "djpunjab");
                    s.put("duration", "3:25");
                    songs.put(s);
                }
            }

            // Albums: /punjabi-music/...-album-12345.html
            Pattern pAlb = Pattern.compile("<a[^>]*href=[\"'](/punjabi-music/[^\"']+-album-(\\d+)\\.html)[\"'][^>]*>(.*?)</a>");
            Matcher mAlb = pAlb.matcher(html);
            while (mAlb.find()) {
                String path = mAlb.group(1);
                String albId = mAlb.group(2);
                String title = mAlb.group(3).replaceAll("<[^>]+>", "").replace("[Album]", "").trim();
                if (!title.isEmpty()) {
                    JSONObject s = new JSONObject();
                    s.put("id", "djpunjab_alb_" + albId);
                    s.put("title", title);
                    s.put("artist", name);
                    s.put("album", title + " [Album]");
                    s.put("cover_url", avatarUrl);
                    s.put("page_url", "https://djpunjab.is" + path);
                    s.put("source", "djpunjab");
                    s.put("duration", "3:40");
                    songs.put(s);
                }
            }

            result.put("slug", cleanSlug);
            result.put("name", name);
            result.put("avatar_url", avatarUrl);
            result.put("source", "djpunjab");
            result.put("song_count", songs.length());
            result.put("songs", songs);
        } catch (Exception e) {
            e.printStackTrace();
        }
        return result.toString();
    }

    @JavascriptInterface
    public String searchOnlineSync(String query) {
        try {
            JSONArray results = new JSONArray();

            List<JSONObject> djSongs = searchDJJohal(query);
            List<JSONObject> mjSongs = searchMrJatt(query);

            int maxLen = Math.max(djSongs.size(), mjSongs.size());
            for (int i = 0; i < maxLen; i++) {
                if (i < djSongs.size()) results.put(djSongs.get(i));
                if (i < mjSongs.size()) results.put(mjSongs.get(i));
            }

            return results.toString();
        } catch (Exception e) {
            e.printStackTrace();
            return "[]";
        }
    }

    @JavascriptInterface
    public String resolveStreamUrlSync(String source, String pageUrl, String streamUrl) {
        try {
            if ("djpunjab".equalsIgnoreCase(source)) {
                if (pageUrl != null && !pageUrl.isEmpty()) {
                    String html = httpGet(pageUrl, "https://djpunjab.is/");
                    Pattern p = Pattern.compile("href=[\"'](https://s320\\.djpunjab\\.is/data/[^\"']+\\.mp3)[\"']");
                    Matcher m = p.matcher(html);
                    while (m.find()) {
                        String link = m.group(1);
                        if (link.contains("/128/")) return link;
                    }
                    m.reset();
                    if (m.find()) return m.group(1);

                    Pattern pSub = Pattern.compile("<a[^>]*href=[\"'](/single-track/[^\"']+-mp3-song-\\d+\\.html)[\"']");
                    Matcher mSub = pSub.matcher(html);
                    if (mSub.find()) {
                        String subUrl = "https://djpunjab.is" + mSub.group(1);
                        String subHtml = httpGet(subUrl, "https://djpunjab.is/");
                        Matcher mSubMp3 = p.matcher(subHtml);
                        while (mSubMp3.find()) {
                            String l = mSubMp3.group(1);
                            if (l.contains("/128/")) return l;
                        }
                        mSubMp3.reset();
                        if (mSubMp3.find()) return mSubMp3.group(1);
                    }
                }
            } else if ("djjohal".equalsIgnoreCase(source)) {
                if (pageUrl != null && !pageUrl.isEmpty()) {
                    String html = httpGet(pageUrl, "https://www.djjohal.com/");
                    Pattern p = Pattern.compile("href=[\"'](https?://[^\"']+\\.mp3[^\"']*)[\"']");
                    Matcher m = p.matcher(html);
                    while (m.find()) {
                        String link = m.group(1);
                        if (link.contains("/128/")) return link;
                    }
                    m.reset();
                    if (m.find()) return m.group(1);
                }
            } else if ("mrjatt".equalsIgnoreCase(source)) {
                if (pageUrl != null && !pageUrl.isEmpty()) {
                    String html = httpGet(pageUrl, "https://www.mr-jatt.im/");
                    Pattern p = Pattern.compile("href=[\"'](https?://cdnsongs\\.com/[^\"']+\\.mp3[^\"']*)[\"']");
                    Matcher m = p.matcher(html);
                    while (m.find()) {
                        String link = m.group(1);
                        if (link.contains("/128/")) return link;
                    }
                    m.reset();
                    if (m.find()) return m.group(1);

                    Pattern pSrc = Pattern.compile("<source[^>]*src=[\"']([^\"']+\\.mp3)[\"']");
                    Matcher mSrc = pSrc.matcher(html);
                    if (mSrc.find()) return mSrc.group(1);
                }
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
        return streamUrl != null ? streamUrl : "";
    }

    @JavascriptInterface
    public String getCachedFileUrlSync(String songId) {
        try {
            File cacheDir = new File(context.getCacheDir(), "music_duniya_cache");
            String cleanId = songId.replaceAll("[^a-zA-Z0-9_-]", "_");
            File targetFile = new File(cacheDir, cleanId + ".mp3");
            if (targetFile.exists() && targetFile.length() > 50000) {
                return "file://" + targetFile.getAbsolutePath();
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
        return "";
    }

    @JavascriptInterface
    public void startCacheDownloadAsync(final String songId, final String source, final String directUrl) {
        executor.execute(() -> downloadToCacheSync(songId, source, directUrl));
    }

    @JavascriptInterface
    public String downloadToCacheSync(String songId, String source, String directUrl) {
        try {
            File cacheDir = new File(context.getCacheDir(), "music_duniya_cache");
            if (!cacheDir.exists()) cacheDir.mkdirs();

            String cleanId = songId.replaceAll("[^a-zA-Z0-9_-]", "_");
            File targetFile = new File(cacheDir, cleanId + ".mp3");

            if (targetFile.exists() && targetFile.length() > 50000) {
                return "file://" + targetFile.getAbsolutePath();
            }

            String referer = "https://www.djjohal.com/";
            if ("djpunjab".equalsIgnoreCase(source)) referer = "https://djpunjab.is/";
            else if ("mrjatt".equalsIgnoreCase(source)) referer = "https://www.mr-jatt.im/";

            URL url = new URL(directUrl);
            HttpURLConnection conn = (HttpURLConnection) url.openConnection();
            conn.setRequestProperty("User-Agent", "Mozilla/5.0 (Linux; Android 14) Chrome/124.0.0.0");
            conn.setRequestProperty("Referer", referer);
            conn.setConnectTimeout(15000);
            conn.setReadTimeout(20000);
            conn.connect();

            if (conn.getResponseCode() == 200) {
                File tempFile = new File(cacheDir, cleanId + ".tmp");
                InputStream in = conn.getInputStream();
                FileOutputStream out = new FileOutputStream(tempFile);
                byte[] buf = new byte[16384];
                int read;
                while ((read = in.read(buf)) != -1) {
                    out.write(buf, 0, read);
                }
                out.flush();
                out.close();
                in.close();

                if (targetFile.exists()) targetFile.delete();
                tempFile.renameTo(targetFile);

                return "file://" + targetFile.getAbsolutePath();
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
        return directUrl;
    }

    @JavascriptInterface
    public String getCachedSongsSync() {
        JSONArray list = new JSONArray();
        try {
            File cacheDir = new File(context.getCacheDir(), "music_duniya_cache");
            if (cacheDir.exists() && cacheDir.isDirectory()) {
                File[] files = cacheDir.listFiles();
                if (files != null) {
                    for (File f : files) {
                        if (f.getName().endsWith(".mp3") && f.length() > 50000) {
                            JSONObject obj = new JSONObject();
                            obj.put("id", f.getName().replace(".mp3", ""));
                            obj.put("title", f.getName().replace(".mp3", "").replace("_", " "));
                            obj.put("artist", "Downloaded Track");
                            obj.put("album", "Local Device Storage");
                            obj.put("cover_url", "https://cover.mr-jatt.im/thumb/default.webp");
                            obj.put("audio_url", "file://" + f.getAbsolutePath());
                            obj.put("file_size_mb", String.format("%.2f MB", f.length() / (1024.0 * 1024.0)));
                            obj.put("source", "cached");
                            list.put(obj);
                        }
                    }
                }
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
        return list.toString();
    }

    @JavascriptInterface
    public boolean clearCacheSync() {
        try {
            File cacheDir = new File(context.getCacheDir(), "music_duniya_cache");
            if (cacheDir.exists() && cacheDir.isDirectory()) {
                File[] files = cacheDir.listFiles();
                if (files != null) {
                    for (File f : files) {
                        f.delete();
                    }
                }
            }
            return true;
        } catch (Exception e) {
            e.printStackTrace();
            return false;
        }
    }

    private List<JSONObject> searchDJJohal(String query) {
        List<JSONObject> list = new ArrayList<>();
        try {
            String url = "https://www.djjohal.com/search.php?q=" + URLEncoder.encode(query, "UTF-8");
            String html = httpGet(url, "https://www.djjohal.com/");

            Pattern p = Pattern.compile("<a[^>]*class=[\"'][^\"']*glass-card[^\"']*[\"'][^>]*href=[\"'](/song/[^\"']+)[\"'][^>]*>.*?<img[^>]*src=[\"']([^\"']+)[\"'].*?<h3[^>]*>([^<]+)</h3>.*?<small[^>]*>([^<]+)</small>", Pattern.DOTALL);
            Matcher m = p.matcher(html);

            while (m.find() && list.size() < 12) {
                String songPath = m.group(1);
                String cover = m.group(2);
                String title = m.group(3).trim();
                String artist = m.group(4).replaceAll("·.*$", "").trim();

                String songId = "djjohal_" + Math.abs(songPath.hashCode());
                JSONObject obj = new JSONObject();
                obj.put("id", songId);
                obj.put("source", "djjohal");
                obj.put("title", title);
                obj.put("artist", artist);
                obj.put("page_url", "https://www.djjohal.com" + songPath);
                obj.put("cover_url", cover.startsWith("http") ? cover : "https://www.djjohal.com" + cover);
                obj.put("stream_url", "");
                obj.put("album", "DJJohal Single");
                list.add(obj);
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
        return list;
    }

    private List<JSONObject> searchMrJatt(String query) {
        List<JSONObject> list = new ArrayList<>();
        try {
            String slug = query.trim().replaceAll("\\s+", "-");
            String url = "https://www.mr-jatt.im/" + slug + "-top-songs.html";
            String html = httpGet(url, "https://www.mr-jatt.im/");

            Pattern p = Pattern.compile("<a[^>]*href=[\"']([^\"']+/song/[^\"']+)[\"'][^>]*>(.*?)</a>");
            Matcher m = p.matcher(html);

            while (m.find() && list.size() < 12) {
                String songPath = m.group(1).split("\\?")[0];
                String rawTitle = m.group(2).replaceAll("<[^>]+>", "").replace("&raquo;", "").replaceAll("^\\d+\\.\\s*", "").replaceAll("\\[R\\]", "").trim();

                String artist = query;
                Matcher mArt = Pattern.compile("\\((.*?)\\)").matcher(rawTitle);
                if (mArt.find()) {
                    artist = mArt.group(1);
                    rawTitle = rawTitle.replaceAll("\\(.*?\\)", "").trim();
                }

                String fullUrl = songPath.startsWith("http") ? songPath : "https://www.mr-jatt.im" + songPath;
                String songId = "mrjatt_" + Math.abs(fullUrl.hashCode());

                JSONObject obj = new JSONObject();
                obj.put("id", songId);
                obj.put("source", "mrjatt");
                obj.put("title", rawTitle);
                obj.put("artist", artist);
                obj.put("page_url", fullUrl);
                obj.put("cover_url", "https://cover.mr-jatt.im/thumb/default.webp");
                obj.put("stream_url", "");
                obj.put("album", "Mr-Jatt Music");
                list.add(obj);
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
        return list;
    }

    private String httpGet(String urlStr, String referer) throws Exception {
        URL url = new URL(urlStr);
        HttpURLConnection conn = (HttpURLConnection) url.openConnection();
        conn.setRequestProperty("User-Agent", "Mozilla/5.0 (Linux; Android 14) Chrome/124.0.0.0");
        if (referer != null) conn.setRequestProperty("Referer", referer);
        conn.setConnectTimeout(8000);
        conn.setReadTimeout(10000);

        BufferedReader reader = new BufferedReader(new InputStreamReader(conn.getInputStream(), "UTF-8"));
        StringBuilder sb = new StringBuilder();
        String line;
        while ((line = reader.readLine()) != null) {
            sb.append(line).append("\n");
        }
        reader.close();
        return sb.toString();
    }

    @JavascriptInterface
    public void updateNotification(final String title, final String artist, final String coverUrl, final boolean isPlaying) {
        mainHandler.post(() -> {
            try {
                android.content.Intent serviceIntent = new android.content.Intent(context, MusicPlaybackService.class);
                serviceIntent.setAction(MusicPlaybackService.ACTION_UPDATE);
                serviceIntent.putExtra("title", title);
                serviceIntent.putExtra("artist", artist);
                serviceIntent.putExtra("coverUrl", coverUrl);
                serviceIntent.putExtra("isPlaying", isPlaying);

                if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.O) {
                    context.startForegroundService(serviceIntent);
                } else {
                    context.startService(serviceIntent);
                }
            } catch (Exception e) {
                e.printStackTrace();
            }
        });
    }

    @JavascriptInterface
    public void cancelNotification() {
        mainHandler.post(() -> {
            try {
                android.content.Intent serviceIntent = new android.content.Intent(context, MusicPlaybackService.class);
                serviceIntent.setAction(MusicPlaybackService.ACTION_STOP);
                context.startService(serviceIntent);
            } catch (Exception ignored) {}
        });
    }
}
