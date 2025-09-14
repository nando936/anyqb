    def delete_payment(self, payment_txn_id: str) -> Dict:
        """
        Delete a bill payment check from QuickBooks
        
        Args:
            payment_txn_id: Transaction ID of the payment to delete
            
        Returns:
            Dictionary with success status
        """
        try:
            if not fast_qb_connection.connect():
                logger.error("Failed to connect to QuickBooks")
                return {"success": False, "error": "Failed to connect to QuickBooks"}
            
            request_set = fast_qb_connection.create_request_set()
            
            # Delete the payment
            delete_rq = request_set.AppendTxnDelRq()
            delete_rq.TxnDelType.SetValue(13)  # 13 = BillPaymentCheck
            delete_rq.TxnID.SetValue(payment_txn_id)
            
            # Process the delete request
            response_set = fast_qb_connection.process_request_set(request_set)
            response = response_set.ResponseList.GetAt(0)
            
            if response.StatusCode == 0:
                logger.info(f"Successfully deleted payment: {payment_txn_id}")
                return {
                    "success": True,
                    "message": f"Payment {payment_txn_id} deleted successfully"
                }
            else:
                # Return the error without voiding fallback
                error_msg = response.StatusMessage if hasattr(response, 'StatusMessage') else f'Error code {response.StatusCode}'
                logger.error(f"Failed to delete payment {payment_txn_id}: {error_msg}")
                return {
                    "success": False,
                    "error": f"Failed to delete payment: {error_msg}"
                }
                
        except Exception as e:
            logger.error(f"Exception in delete_payment: {str(e)}")
            return {
                "success": False,
                "error": f"Exception: {str(e)}"
            }
        finally:
            fast_qb_connection.disconnect()