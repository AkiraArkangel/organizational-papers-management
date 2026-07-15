// Status Summary Click Handler
document.addEventListener('DOMContentLoaded', function() {
    const statusItems = document.querySelectorAll('.clickable-status');
    
    statusItems.forEach(item => {
        item.addEventListener('click', function() {
            const status = this.getAttribute('data-status');
            scrollToFirstDocumentWithStatus(status);
        });
        
        // Add cursor pointer to indicate clickability
        item.style.cursor = 'pointer';
    });
    
    function scrollToFirstDocumentWithStatus(status) {
        // Find all document rows with the specified status
        const statusMap = {
            'SUBMITTED': 'submitted',
            'PENDING_ADVISER': 'pending-adviser',
            'APPROVED_BY_ADVISER': 'approved-by-adviser',
            'CORRECTED': 'corrected',
            'RESUBMITTED': 'resubmitted',
            'APPROVED_BY_COI': 'approved-by-coi',
            'READY_FOR_PRINTING': 'ready-for-printing'
        };
        
        const statusClass = statusMap[status];
        if (!statusClass) return;
        
        // Find the first document with this status
        const targetDocument = document.querySelector(`.document-row[data-status="${status}"]`);
        
        if (targetDocument) {
            // Highlight the document
            targetDocument.classList.add('highlighted-document');
            
            // Scroll to it
            targetDocument.scrollIntoView({ behavior: 'smooth', block: 'center' });
            
            // Remove highlight after animation
            setTimeout(() => {
                targetDocument.classList.remove('highlighted-document');
            }, 2000);
        } else {
            // If no document found, show a message
            alert(`No files found with status: ${status.replace(/_/g, ' ')}`);
        }
    }
});
