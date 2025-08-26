// Modal functionality
function openModal(modalId) {
    document.getElementById(modalId).style.display = 'block';
    document.body.style.overflow = 'hidden'; // Prevent background scrolling
}

function closeModal(modalId) {
    document.getElementById(modalId).style.display = 'none';
    document.body.style.overflow = 'auto'; // Restore scrolling
}

// Open article in new window/tab
function openArticlePage(articleId) {
    const article = blogManager.articles.find(a => a.id === articleId);
    if (!article) return;
    
    const articleHTML = `
<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>${article.title} - Gagdus</title>
    <link rel="stylesheet" href="css/style.css">
    <style>
        .article-page { max-width: 800px; margin: 40px auto; padding: 40px; background: white; border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.1); }
        .article-page h1 { color: #2c3e50; margin-bottom: 20px; font-size: 2.5rem; }
        .article-page .content { color: #495057; line-height: 1.8; font-size: 1.1rem; }
        .back-btn { display: inline-block; margin-bottom: 30px; padding: 12px 24px; background: #007bff; color: white; text-decoration: none; border-radius: 8px; font-size: 1.1rem; }
        .back-btn:hover { background: #0056b3; }
    </style>
</head>
<body>
    <div class="article-page">
        <a href="javascript:window.close()" class="back-btn">← Geri Dön</a>
        <h1>${article.title}</h1>
        <div class="content">${article.content}</div>
    </div>
</body>
</html>`;
    
    const newWindow = window.open('', '_blank', 'width=1000,height=800,scrollbars=yes,resizable=yes');
    newWindow.document.write(articleHTML);
    newWindow.document.close();
}

// Close modal when clicking outside of it
window.onclick = function(event) {
    const modals = document.querySelectorAll('.modal');
    modals.forEach(modal => {
        if (event.target === modal) {
            modal.style.display = 'none';
            document.body.style.overflow = 'auto';
        }
    });
}

// Close modal with Escape key
document.addEventListener('keydown', function(event) {
    if (event.key === 'Escape') {
        const modals = document.querySelectorAll('.modal');
        modals.forEach(modal => {
            if (modal.style.display === 'block') {
                modal.style.display = 'none';
                document.body.style.overflow = 'auto';
            }
        });
    }
});

// Dynamic article management
class BlogManager {
    constructor() {
        this.articles = this.loadArticles();
        this.init();
    }

    init() {
        this.loadDynamicArticles();
        this.generateDynamicModals();
    }

    // Load articles from localStorage
    loadArticles() {
        const stored = localStorage.getItem('blogArticles');
        if (stored) {
            return JSON.parse(stored);
        }
        
        // Default articles if none exist
        return [
            {
                id: 1,
                title: '5 Saatlik İş Günü',
                excerpt: '8 saatlik iş günü modası geçti. Bu yüzden 5 saatlik iş gününü benimsemeyi seçtim.',
                content: `8 saatlik iş günü modası geçti. Bu yüzden 5 saatlik iş gününü benimsemeyi seçtim.

<h3>Neden 5 Saat?</h3>
<p>Geleneksel 8 saatlik iş gününün kökleri Sanayi Devrimine dayanıyor. O zamanlar fabrika işçileri için mantıklı olan bu sistem, bugünün bilgi çağında artık verimli değil.</p>

<p>Modern araştırmalar gösteriyor ki, ortalama bir bilgi işçisi günde sadece 2.5-3 saat verimli çalışabiliyor. Geri kalan zaman toplantılarda, e-postalar arasında ve dikkat dağınıklığı ile geçiyor.</p>

<h3>5 Saatlik İş Gününün Faydaları</h3>
<p>• <strong>Daha yüksek verimlilik:</strong> Kısıtlı zaman, odaklanmayı artırıyor</p>
<p>• <strong>Daha iyi yaşam kalitesi:</strong> Ailene ve hobilerine daha fazla zaman</p>
<p>• <strong>Azalan stres:</strong> İş-yaşam dengesinde iyileşme</p>
<p>• <strong>Yaratıcılığın artması:</strong> Dinlenmiş beyin daha yaratıcı çözümler üretiyor</p>

<h3>Nasıl Uygulanır?</h3>
<p>5 saatlik iş gününe geçiş kademeli olmalı. İlk olarak en önemli görevlerinizi belirleyin ve bunlara odaklanın. Toplantıları azaltın, dikkat dağıtıcı faktörleri ortadan kaldırın ve Pomodoro Tekniği gibi zaman yönetimi araçlarını kullanın.</p>

<p>Unutmayın: Amaç daha az çalışmak değil, daha akıllı çalışmaktır.</p>`,
                image: 'article-1',
                createdAt: new Date().toISOString()
            },
            {
                id: 2,
                title: 'Gelecekteki Çocuklarıma Vereceğim Finansal Tavsiye: Sahip Ol',
                excerpt: 'Finansal Gagdus yolunda vereceğim en önemli tavsiye basit ama güçlü: Sahip olmayı öğrenin.',
                content: `Finansal Gagdus yolunda vereceğim en önemli tavsiye basit ama güçlü: <strong>Sahip olmayı öğrenin.</strong>

<h3>Sahiplik vs Çalışmak</h3>
<p>Geleneksel iş modelinde zamanınızı paraya çevirirsiniz. Ancak günde sadece 24 saat vardır ve bu sınırlama sizi kısıtlar. Sahiplik ise farklı bir oyun kuralı sunar.</p>

<p>Sahip olduğunuzda - hisse senetleri, emlak, işletme veya fikri mülkiyet - paranız sizin için çalışır. Bu, pasif gelir yaratmanın anahtarıdır.</p>

<h3>Sahiplik Türleri</h3>
<p>• <strong>Hisse Senetleri:</strong> Şirketlerin bir parçasına sahip olmak</p>
<p>• <strong>Emlak:</strong> Kira geliri sağlayan mülkler</p>
<p>• <strong>İş Kurma:</strong> Kendi şirketinizi yaratmak</p>
<p>• <strong>Fikri Mülkiyet:</strong> Patent, telif hakkı, marka</p>

<h3>Nasıl Başlanır?</h3>
<p>Sahiplik yolculuğu küçük adımlarla başlar. İlk olarak acil durum fonu oluşturun, sonra düşük maliyetli endeks fonlarına yatırım yapmaya başlayın. Zamanla portföyünüzü çeşitlendirin ve farklı sahiplik türlerini keşfedin.</p>

<p>Unutmayın: En önemli yatırım kendinizdir. Sürekli öğrenin, becerilerinizi geliştirin ve değer yaratmaya odaklanın.</p>`,
                image: 'article-2',
                createdAt: new Date().toISOString()
            }
        ];
    }

    // Load dynamic articles into the main content area
    loadDynamicArticles() {
        const contentArea = document.querySelector('.content-area');
        if (!contentArea) return;

        // Clear existing static articles
        contentArea.innerHTML = '';

        // Generate article cards
        this.articles.forEach((article, index) => {
            const articleCard = document.createElement('article');
            articleCard.className = 'article-card';
            articleCard.onclick = () => openArticlePage(article.id);
            
            articleCard.innerHTML = `
                <div class="article-image ${article.image}"></div>
                <div class="article-content">
                    <h2 class="article-title">${article.title}</h2>
                    <p class="article-excerpt">${article.excerpt}</p>
                </div>
            `;
            
            contentArea.appendChild(articleCard);
        });
    }

    // Generate dynamic modals for articles
    generateDynamicModals() {
        // Remove existing dynamic modals
        const existingModals = document.querySelectorAll('[id^="dynamicModal"]');
        existingModals.forEach(modal => modal.remove());

        // Generate new modals
        this.articles.forEach(article => {
            const modal = document.createElement('div');
            modal.id = `dynamicModal${article.id}`;
            modal.className = 'modal';
            
            modal.innerHTML = `
                <div class="modal-content">
                    <div class="modal-header">
                        <h2 class="modal-title">${article.title}</h2>
                        <span class="close" onclick="closeModal('dynamicModal${article.id}')">&times;</span>
                    </div>
                    <div class="modal-body">
                        ${article.content}
                    </div>
                </div>
            `;
            
            document.body.appendChild(modal);
        });
    }

    // Get articles for search
    getArticlesForSearch() {
        return this.articles.map(article => ({
            title: article.title,
            excerpt: article.excerpt,
            modalId: `dynamicModal${article.id}`
        }));
    }
}

// Search functionality
function performSearch() {
    const searchInput = document.getElementById('searchInput');
    const searchResults = document.getElementById('searchResults');
    const query = searchInput.value.toLowerCase().trim();
    
    if (query === '') {
        searchResults.style.display = 'none';
        return;
    }
    
    // Get articles from blog manager
    const articles = window.blogManager ? window.blogManager.getArticlesForSearch() : [];
    
    // Filter articles based on search query
    const filteredArticles = articles.filter(article => 
        article.title.toLowerCase().includes(query) || 
        article.excerpt.toLowerCase().includes(query)
    );
    
    // Display search results
    if (filteredArticles.length > 0) {
        let resultsHTML = '';
        filteredArticles.forEach(article => {
            resultsHTML += `
                <div class="search-result-item" onclick="openModal('${article.modalId}')">
                    <div class="search-result-title">${article.title}</div>
                    <div class="search-result-excerpt">${article.excerpt}</div>
                </div>
            `;
        });
        searchResults.innerHTML = resultsHTML;
        searchResults.style.display = 'block';
    } else {
        searchResults.innerHTML = '<div class="search-result-item">Arama sonucu bulunamadı.</div>';
        searchResults.style.display = 'block';
    }
}

// Search on Enter key press
document.addEventListener('DOMContentLoaded', function() {
    const searchForm = document.querySelector('.search-form');
    const searchInput = document.querySelector('.search-input');
    
    if (searchForm && searchInput) {
        searchForm.addEventListener('submit', function(e) {
            if (searchInput.value.trim() === '') {
                e.preventDefault();
                alert('Lütfen arama terimi girin.');
            }
        });
    }
});

// Delete post functionality
function deletePost(postId) {
    if (confirm('Bu yazıyı silmek istediğinizden emin misiniz?')) {
        fetch(`/admin/posts/delete/${postId}`, {
            method: 'GET'
        })
        .then(response => {
            if (response.ok) {
                location.reload();
            } else {
                alert('Yazı silinirken hata oluştu.');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Yazı silinirken hata oluştu.');
        });
    }
}

// Smooth scrolling for navigation links
document.addEventListener('DOMContentLoaded', function() {
    const navLinks = document.querySelectorAll('.nav-menu a[href^="#"]');
    navLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const targetId = this.getAttribute('href').substring(1);
            const targetElement = document.getElementById(targetId);
            if (targetElement) {
                targetElement.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });
});

// Initialize blog manager and add loading animation for article cards
document.addEventListener('DOMContentLoaded', function() {
    // Initialize blog manager
    // Disabled to prevent overriding server-rendered posts
    // window.blogManager = new BlogManager();
    
    // Wait a bit for articles to load, then apply animations
    setTimeout(() => {
        const articleCards = document.querySelectorAll('.article-card');
        
        // Add intersection observer for fade-in animation
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.style.opacity = '1';
                    entry.target.style.transform = 'translateY(0)';
                }
            });
        }, {
            threshold: 0.1,
            rootMargin: '0px 0px -50px 0px'
        });
        
        articleCards.forEach(card => {
            card.style.opacity = '0';
            card.style.transform = 'translateY(30px)';
            card.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
            observer.observe(card);
        });
    }, 100);
});