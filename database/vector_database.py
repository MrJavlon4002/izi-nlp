import weaviate
from weaviate.classes.config import Configure, Property, DataType
import api_keys

class WeaviateDatabase:
    def __init__(self):
        self.headers = {"X-VoyageAI-Api-Key": api_keys.VOYAGE_API_KEY}

    def _create_client(self):
        return weaviate.connect_to_local(host="localhost", port=8080, headers=self.headers)

    def initialize_and_insert_data(self, row_data, project_name: str):
        project_name = project_name.lower()
        with self._create_client() as client:
            client.collections.delete_all()
            print("Existing collections deleted.")
            for lang, chunks in row_data.items():
                collection_name = f"{project_name}_{lang}"
                self._ensure_collection_exists(client, collection_name)

                collection = client.collections.get(collection_name)

                with collection.batch.dynamic() as batch:
                    for idx, chunk_data in enumerate(chunks.values()):
                        batch.add_object(
                            properties={
                                "title": chunk_data["title"],
                                "text": chunk_data["text"],
                                "number": idx,
                            }
                        )

                        if batch.number_errors > 10:
                            print("Batch import stopped due to excessive errors.")
                            break

                print(f"Inserted data into collection '{collection_name}'.")

                
    def _ensure_collection_exists(self, client, collection_name):
        if not client.collections.exists(collection_name):
            client.collections.create(
                collection_name,
                vectorizer_config=[
                    Configure.NamedVectors.text2vec_voyageai(
                        name="text_vector",
                        source_properties=["text", "title"],
                        model="voyage-3",
                    ),
                ]
            )
            print(f"Collection '{collection_name}' created with VoyageAI vectorizer.")
        else:
            print(f"Collection '{collection_name}' already exists.")
    
    def delete_collection(self, project_name: str):
        project_name = project_name.lower()
        with self._create_client() as client:
            collections = client.collections.list_all()
            if not collections:
                print("No collections found.")
                return False
            for collection in collections:
                if collection.name == project_name:
                    client.collections.delete(collection.name)
                    print(f"Collection '{project_name}' deleted.")
                    return True
            print(f"Collection '{project_name}' does not exist.")
            return False
                

    def check_collection(self, project_name: str):
        project_name = project_name.lower()
        with self._create_client() as client:
            collections = client.collections.list_all()
            if not collections:
                print("No collections found.")
                return False
            for collection in collections:
                if collection.name == project_name:
                    print(f"Collection '{project_name}' exists.")
                    return True
            print(f"Collection '{project_name}' does not exist.")
            return False
    

    def add_product(self, project_name: str, details: dict):
        """Adds a product to the vector database."""
        name = details['name']
        description = details['description']
        price = details['price']
        id = details['id']
        project_name = project_name.lower()
        with self._create_client() as client:
            if not client.collections.exists(project_name):
                print(f"Collection '{project_name}' does not exist.")
                return False

            try:
                collection = client.collections.get(project_name)
                with collection.batch.dynamic() as batch:
                    batch.add_object(
                        properties={
                            "name": name,
                            "description": description,
                            "price": price,
                        },
                        uuid=id,
                    )
                print(f"Product added to collection '{project_name}'.")
                return True
            except Exception as e:
                print(f"Error adding product: {e}")
                return False
            finally:
                client.close()
    
    def get_product(self, product_id: str, project_name: str):
        """Retrieves a product from the vector database."""
        collection_name = project_name.lower()
        with self._create_client() as client:
            if not client.collections.exists(collection_name):
                print(f"Collection '{collection_name}' does not exist.")
                return None

            collection = client.collections.get(collection_name)
            try:
                response = collection.query.fetch_object_by_id(product_id)
                if response:
                    return response.properties
                else:
                    print(f"Product with ID '{product_id}' not found in collection '{collection_name}'.")
                    return None
            except Exception as e:
                print(f"Error retrieving product: {e}")
                return None
            finally:
                client.close()

    def get_all_product(self, collection_name: str):
        """Retrieves a product from the vector database."""
        with self._create_client() as client:
            if not client.collections.exists(collection_name):
                print(f"Collection '{collection_name}' does not exist.")
                return None

            collection = client.collections.get(collection_name)
            try:
                all_products = []
                for item in collection.iterator():
                    all_products.append(item.properties)
                return all_products
            except Exception as e:
                print(f"Error retrieving products: {e}")
                return None
            finally:
                client.close()

    
    def update_product(self, project_name: str, details: dict):
        """Updates a product in the vector database."""
        name = details['name']
        description = details['description']
        price = details['price']
        id = details['id']
        project_name = project_name.lower()

        with self._create_client() as client:
            if not client.collections.exists(project_name):
                print(f"Collection '{project_name}' does not exist.")
                return False

            collection = client.collections.get(project_name)
            try:
                collection.objects.update(
                    uuid=id,
                    properties={
                        "name": name,
                        "description": description,
                        "price": price,
                    },
                )
                print(f"Product with ID '{id}' updated in collection '{project_name}'.")
            except Exception as e:
                print(f"Error updating product: {e}")
                return False
            finally:
                client.close()
                print(f"Product with ID '{id}' not found in collection '{project_name}'.")
            return True

    def delete_product(self, project_name: str, product_id: str):
        """Deletes a product from the vector database."""
        project_name = project_name.lower()
        with self._create_client() as client:
            if not client.collections.exists(project_name):
                print(f"Collection '{project_name}' does not exist.")
                return False

            collection = client.collections.get(project_name)
            try:
                collection.data.delete_by_id(product_id)
                print(f"Product with ID '{product_id}' deleted from collection '{project_name}'.")
            except Exception as e:
                print(f"Error deleting product: {e}")
                return False
            finally:
                client.close()


    def hybrid_query(self, query: str, collection_name, limit=3):
        client = None
        try:
            client = self._create_client()
            if not client.collections.exists(collection_name):
                print(client.collections.list_all())
                print(f"Collection '{collection_name}' not found.")
                return []

            collection = client.collections.get(collection_name)
            if isinstance(query, list): 
                query = ' '.join(query)

            response = collection.query.hybrid(
                query=query,
                limit=limit,
                alpha=0.7,
            )
            return [{
                'text': obj.properties.get('text', ''),
                'title': obj.properties.get('title', ''),
                'number': obj.properties.get('number', ''),
                'name': obj.properties.get('name', ''),
                'description': obj.properties.get('description', ''),
                'price': obj.properties.get('price', ''),
                'id': obj.uuid,
            } for obj in response.objects]


        except Exception as e:
            print(f"Error during query: {e}")
            return []
        finally:
            if client:
                client.close()